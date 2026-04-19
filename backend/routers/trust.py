from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from .. import models, schemas, exceptions
from ..database import get_db
from ..core.limiter import limiter
from .auth_router import get_current_user

router = APIRouter(prefix="/trust", tags=["Trust"])


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_str(value: Any, default: str = "") -> str:
    if isinstance(value, str):
        return value
    return default


def _compute_risk_flags(db: Session, current_user: models.User) -> list[str]:
    user_id = _as_int(getattr(current_user, "id", 0))
    role = _as_str(getattr(current_user, "role", "")).lower()
    flags: list[str] = []

    if role == "sponsor":
        deals_query = db.query(models.Deal).filter(models.Deal.sponsor_id == user_id)
    elif role == "organizer":
        deals_query = db.query(models.Deal).filter(models.Deal.organizer_id == user_id)
    else:
        deals_query = db.query(models.Deal).filter(models.Deal.influencer_id == user_id)

    total_deals = deals_query.count()
    rejected_deals = deals_query.filter(models.Deal.status == "rejected").count()
    if total_deals >= 5 and rejected_deals / max(total_deals, 1) >= 0.6:
        flags.append("high_rejection_rate")

    unsigned_paid = deals_query.filter(
        models.Deal.payment_done == True,
        ((models.Deal.sponsor_signed == False) | (models.Deal.organizer_signed == False))
    ).count()
    if unsigned_paid > 0:
        flags.append("payment_signed_mismatch")

    reuse_events = db.query(models.AuditEvent).filter(
        models.AuditEvent.actor_user_id == user_id,
        models.AuditEvent.action == "auth.refresh_reuse_detected"
    ).count()
    if reuse_events > 0:
        flags.append("token_reuse_signal")

    since = datetime.utcnow() - timedelta(hours=24)
    if role == "sponsor":
        recent_deals = db.query(models.Deal).filter(models.Deal.sponsor_id == user_id, models.Deal.created_at >= since).count()
    elif role == "organizer":
        recent_deals = db.query(models.Deal).filter(models.Deal.organizer_id == user_id, models.Deal.created_at >= since).count()
    else:
        recent_deals = db.query(models.Deal).filter(models.Deal.influencer_id == user_id, models.Deal.created_at >= since).count()

    if recent_deals >= 10:
        flags.append("proposal_spike_24h")

    has_kyc = db.query(models.KYCSubmission).filter(models.KYCSubmission.user_id == user_id).count() > 0
    if not has_kyc:
        flags.append("kyc_not_submitted")

    return sorted(set(flags))


def _risk_level(flags: list[str]) -> str:
    high_signals = {"token_reuse_signal", "payment_signed_mismatch"}
    if any(f in high_signals for f in flags):
        return "high"
    if len(flags) >= 2:
        return "medium"
    return "low"


@router.post("/kyc/submit", response_model=schemas.KYCSubmissionResponse)
@limiter.limit("10/minute")
def submit_kyc(
    request: Request,
    payload: schemas.KYCSubmissionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    user_id = _as_int(getattr(current_user, "id", 0))

    pending = db.query(models.KYCSubmission).filter(
        models.KYCSubmission.user_id == user_id,
        models.KYCSubmission.status == "pending"
    ).first()
    if pending:
        raise exceptions.ValidationError("A KYC submission is already pending review")

    submission = models.KYCSubmission(
        user_id=user_id,
        document_type=payload.document_type,
        document_number_masked=payload.document_number_masked,
        document_url=payload.document_url,
        status="pending",
        risk_score=0,
        risk_flags=[],
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return submission


@router.get("/me", response_model=schemas.TrustProfileResponse)
@limiter.limit("120/minute")
def get_my_trust_profile(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    user_id = _as_int(getattr(current_user, "id", 0))
    latest_submission = db.query(models.KYCSubmission).filter(
        models.KYCSubmission.user_id == user_id
    ).order_by(models.KYCSubmission.submitted_at.desc()).first()

    risk_flags = _compute_risk_flags(db, current_user)

    if latest_submission is None:
        kyc_status = "not_submitted"
    else:
        kyc_status = _as_str(getattr(latest_submission, "status", "pending"), default="pending")

    return {
        "verification_badge": bool(getattr(current_user, "verification_badge", False)),
        "trust_score": getattr(current_user, "trust_score", 5),
        "kyc_status": kyc_status,
        "latest_submission": latest_submission,
        "risk_flags": risk_flags,
        "risk_level": _risk_level(risk_flags),
    }


@router.get("/kyc/pending", response_model=list[schemas.KYCSubmissionResponse])
@limiter.limit("60/minute")
def get_pending_kyc(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if _as_str(getattr(current_user, "role", "")).lower() != "admin":
        raise exceptions.AuthorizationError("Only admins can review KYC submissions")

    return db.query(models.KYCSubmission).filter(models.KYCSubmission.status == "pending").order_by(
        models.KYCSubmission.submitted_at.asc()
    ).all()


@router.put("/kyc/{submission_id}/review", response_model=schemas.KYCSubmissionResponse)
@limiter.limit("60/minute")
def review_kyc(
    request: Request,
    submission_id: int,
    payload: schemas.KYCReviewRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if _as_str(getattr(current_user, "role", "")).lower() != "admin":
        raise exceptions.AuthorizationError("Only admins can review KYC submissions")

    submission = db.query(models.KYCSubmission).filter(models.KYCSubmission.id == submission_id).first()
    if not submission:
        raise exceptions.ValidationError("KYC submission not found")

    submission_status = _as_str(getattr(submission, "status", ""))
    if submission_status != "pending":
        raise exceptions.ValidationError("KYC submission already reviewed")

    setattr(submission, "status", payload.decision)
    setattr(submission, "reviewer_id", _as_int(getattr(current_user, "id", 0)))
    setattr(submission, "review_note", payload.review_note)
    setattr(submission, "reviewed_at", datetime.utcnow())
    if payload.risk_score is not None:
        setattr(submission, "risk_score", max(0, min(100, _as_int(payload.risk_score))))
    if payload.risk_flags is not None:
        setattr(submission, "risk_flags", payload.risk_flags)

    target_user = db.query(models.User).filter(models.User.id == submission.user_id).first()
    if target_user is None:
        raise exceptions.ValidationError("Submission user not found")

    if payload.decision == "approved":
        setattr(target_user, "verification_badge", True)
    else:
        setattr(target_user, "verification_badge", False)

    db.commit()
    db.refresh(submission)
    return submission
