from __future__ import annotations

import csv
import io
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from .. import exceptions, models, schemas
from ..core.limiter import limiter
from ..database import get_db
from .auth_router import get_current_user

router = APIRouter(prefix="/reports", tags=["Reporting"])


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_str(value: Any, default: str = "") -> str:
    if isinstance(value, str):
        return value
    return default


def _to_decimal(value: Any) -> Decimal:
    return Decimal(str(value or 0))


def _deals_for_user(db: Session, user: models.User, period_days: int | None = None) -> list[models.Deal]:
    user_id = _as_int(getattr(user, "id", 0))
    role = _as_str(getattr(user, "role", "")).lower()
    query = db.query(models.Deal)

    if role == "sponsor":
        query = query.filter(models.Deal.sponsor_id == user_id)
    elif role == "organizer":
        query = query.filter(models.Deal.organizer_id == user_id)
    elif role == "influencer":
        query = query.filter(models.Deal.influencer_id == user_id)
    else:
        query = query.filter(models.Deal.id == -1)

    if period_days is not None and period_days > 0:
        since = datetime.utcnow() - timedelta(days=period_days)
        query = query.filter(models.Deal.created_at >= since)

    return query.all()


def _store_snapshot(db: Session, user_id: int, report_type: str, period_key: str, data_json: dict[str, Any], exported_format: str | None = None) -> None:
    snapshot = models.ReportSnapshot(
        user_id=user_id,
        report_type=report_type,
        period_key=period_key,
        data_json=data_json,
        exported_format=exported_format,
    )
    db.add(snapshot)
    db.commit()


@router.get("/roi", response_model=schemas.ROIReportResponse)
@limiter.limit("90/minute")
def roi_report(
    request: Request,
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    del request
    period_days = max(7, min(365, int(days)))
    deals = _deals_for_user(db, current_user, period_days=period_days)

    total_deals = len(deals)
    closed_deals = sum(1 for d in deals if _as_str(getattr(d, "status", "")) == "closed")
    active_deals = sum(1 for d in deals if _as_str(getattr(d, "status", "")) not in {"closed", "rejected"})
    total_value = sum((_to_decimal(getattr(d, "payment_amount", 0)) for d in deals), Decimal("0"))
    paid_value = sum((_to_decimal(getattr(d, "payment_amount", 0)) for d in deals if bool(getattr(d, "payment_done", False))), Decimal("0"))
    conversion_rate = round((closed_deals / total_deals) * 100.0, 2) if total_deals else 0.0
    avg_deal_value = (total_value / total_deals) if total_deals else Decimal("0")

    response = schemas.ROIReportResponse(
        role=_as_str(getattr(current_user, "role", "")),
        total_deals=total_deals,
        closed_deals=closed_deals,
        active_deals=active_deals,
        conversion_rate=conversion_rate,
        total_value=total_value,
        paid_value=paid_value,
        avg_deal_value=avg_deal_value,
        period_days=period_days,
    )
    _store_snapshot(
        db,
        user_id=_as_int(getattr(current_user, "id", 0)),
        report_type="roi",
        period_key=f"last_{period_days}_days",
        data_json=response.model_dump(mode="json"),
    )
    return response


def _campaign_outcome_rows(db: Session, current_user: models.User) -> list[schemas.CampaignOutcomeRow]:
    user_id = _as_int(getattr(current_user, "id", 0))
    role = _as_str(getattr(current_user, "role", ""))

    rows: list[schemas.CampaignOutcomeRow] = []
    if role == "sponsor":
        campaign_rows = (
            db.query(
                models.Campaign.id.label("id"),
                models.Campaign.title.label("title"),
                models.Campaign.status.label("status"),
                models.Campaign.budget.label("budget"),
                func.count(models.Deal.id).label("linked_deals"),
                func.coalesce(
                    func.sum(case((models.Deal.status == "closed", 1), else_=0)),
                    0,
                ).label("closed_deals"),
            )
            .outerjoin(models.Deal, models.Deal.campaign_id == models.Campaign.id)
            .filter(models.Campaign.creator_id == user_id)
            .group_by(
                models.Campaign.id,
                models.Campaign.title,
                models.Campaign.status,
                models.Campaign.budget,
            )
            .all()
        )

        for row in campaign_rows:
            linked_count = _as_int(getattr(row, "linked_deals", 0))
            closed_count = _as_int(getattr(row, "closed_deals", 0))
            conversion = round((closed_count / linked_count) * 100.0, 2) if linked_count else 0.0
            rows.append(
                schemas.CampaignOutcomeRow(
                    id=_as_int(getattr(row, "id", 0)),
                    title=_as_str(getattr(row, "title", "")),
                    status=_as_str(getattr(row, "status", "open")),
                    budget=_to_decimal(getattr(row, "budget", 0)),
                    linked_deals=linked_count,
                    closed_deals=closed_count,
                    conversion_rate=conversion,
                )
            )
    elif role == "organizer":
        event_rows = (
            db.query(
                models.Event.id.label("id"),
                models.Event.title.label("title"),
                models.Event.raw_budget.label("budget"),
                func.count(models.Deal.id).label("linked_deals"),
                func.coalesce(
                    func.sum(case((models.Deal.status == "closed", 1), else_=0)),
                    0,
                ).label("closed_deals"),
            )
            .outerjoin(models.Deal, models.Deal.event_id == models.Event.id)
            .filter(models.Event.organizer_id == user_id)
            .group_by(models.Event.id, models.Event.title, models.Event.raw_budget)
            .all()
        )

        for row in event_rows:
            linked_count = _as_int(getattr(row, "linked_deals", 0))
            closed_count = _as_int(getattr(row, "closed_deals", 0))
            conversion = round((closed_count / linked_count) * 100.0, 2) if linked_count else 0.0
            rows.append(
                schemas.CampaignOutcomeRow(
                    id=_as_int(getattr(row, "id", 0)),
                    title=_as_str(getattr(row, "title", "")),
                    status="published",
                    budget=_to_decimal(getattr(row, "budget", 0)),
                    linked_deals=linked_count,
                    closed_deals=closed_count,
                    conversion_rate=conversion,
                )
            )
    elif role == "influencer":
        campaign_rows = (
            db.query(
                models.Campaign.id.label("id"),
                models.Campaign.title.label("title"),
                models.Campaign.status.label("status"),
                models.Campaign.budget.label("budget"),
                func.count(models.Deal.id).label("linked_deals"),
                func.coalesce(
                    func.sum(case((models.Deal.status == "closed", 1), else_=0)),
                    0,
                ).label("closed_deals"),
            )
            .join(models.Deal, models.Deal.campaign_id == models.Campaign.id)
            .filter(models.Deal.influencer_id == user_id)
            .group_by(
                models.Campaign.id,
                models.Campaign.title,
                models.Campaign.status,
                models.Campaign.budget,
            )
            .all()
        )

        for row in campaign_rows:
            linked_count = _as_int(getattr(row, "linked_deals", 0))
            closed_count = _as_int(getattr(row, "closed_deals", 0))
            conversion = round((closed_count / linked_count) * 100.0, 2) if linked_count else 0.0
            rows.append(
                schemas.CampaignOutcomeRow(
                    id=_as_int(getattr(row, "id", 0)),
                    title=_as_str(getattr(row, "title", "")),
                    status=_as_str(getattr(row, "status", "open")),
                    budget=_to_decimal(getattr(row, "budget", 0)),
                    linked_deals=linked_count,
                    closed_deals=closed_count,
                    conversion_rate=conversion,
                )
            )
    else:
        return []
    return rows


@router.get("/campaign-outcomes", response_model=list[schemas.CampaignOutcomeRow])
@limiter.limit("80/minute")
def campaign_outcomes(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    del request
    rows = _campaign_outcome_rows(db, current_user)
    _store_snapshot(
        db,
        user_id=_as_int(getattr(current_user, "id", 0)),
        report_type="campaign_outcome",
        period_key=datetime.utcnow().strftime("%Y-%m-%d"),
        data_json={"rows": [r.model_dump(mode="json") for r in rows]},
    )
    return rows


@router.get("/campaign-outcomes/export.csv")
@limiter.limit("40/minute")
def export_campaign_outcomes_csv(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    del request
    rows = _campaign_outcome_rows(db, current_user)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "title", "status", "budget", "linked_deals", "closed_deals", "conversion_rate"])
    for row in rows:
        writer.writerow([row.id, row.title, row.status, str(row.budget), row.linked_deals, row.closed_deals, row.conversion_rate])
    csv_text = output.getvalue()

    _store_snapshot(
        db,
        user_id=_as_int(getattr(current_user, "id", 0)),
        report_type="campaign_outcome",
        period_key=datetime.utcnow().strftime("%Y-%m-%d"),
        data_json={"rows": [r.model_dump(mode="json") for r in rows]},
        exported_format="csv",
    )
    filename = f"campaign-outcomes-{datetime.utcnow().strftime('%Y%m%d')}.csv"
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/monthly-executive", response_model=schemas.MonthlyExecutiveReportResponse)
@limiter.limit("70/minute")
def monthly_executive_report(
    request: Request,
    month: str | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    del request
    now = datetime.utcnow()
    month_key = month or now.strftime("%Y-%m")
    try:
        month_start = datetime.strptime(f"{month_key}-01", "%Y-%m-%d")
    except ValueError:
        raise exceptions.ValidationError("month should be in YYYY-MM format")
    if month_start.month == 12:
        month_end = datetime(month_start.year + 1, 1, 1)
    else:
        month_end = datetime(month_start.year, month_start.month + 1, 1)

    user_id = _as_int(getattr(current_user, "id", 0))
    role = _as_str(getattr(current_user, "role", "")).lower()

    query = db.query(models.Deal).filter(models.Deal.created_at >= month_start, models.Deal.created_at < month_end)
    if role == "sponsor":
        query = query.filter(models.Deal.sponsor_id == user_id)
    elif role == "organizer":
        query = query.filter(models.Deal.organizer_id == user_id)
    else:
        query = query.filter(models.Deal.influencer_id == user_id)
    deals = query.all()

    total = len(deals)
    closed = sum(1 for d in deals if _as_str(getattr(d, "status", "")) == "closed")
    pending_signatures = sum(
        1 for d in deals if _as_str(getattr(d, "status", "")) == "signing_pending"
    )
    paid = sum(1 for d in deals if bool(getattr(d, "payment_done", False)))
    value = sum((_to_decimal(getattr(d, "payment_amount", 0)) for d in deals), Decimal("0"))
    paid_value = sum((_to_decimal(getattr(d, "payment_amount", 0)) for d in deals if bool(getattr(d, "payment_done", False))), Decimal("0"))
    conversion = round((closed / total) * 100.0, 2) if total else 0.0

    highlights: list[str] = []
    risks: list[str] = []
    if closed > 0:
        highlights.append(f"{closed} deals closed in {month_key}.")
    if paid > 0:
        highlights.append(f"{paid} deals reached paid state with value {paid_value} INR.")
    if pending_signatures > 0:
        risks.append(f"{pending_signatures} deals are waiting for signatures.")
    if conversion < 25 and total >= 4:
        risks.append("Conversion rate is below 25%; review qualification criteria.")
    if not risks:
        risks.append("No major risk signal detected in this period.")

    report = schemas.MonthlyExecutiveReportResponse(
        month=month_key,
        role=role,
        kpis={
            "deals_created": total,
            "deals_closed": closed,
            "conversion_rate": conversion,
            "booked_value_inr": str(value),
            "paid_value_inr": str(paid_value),
            "pending_signatures": pending_signatures,
        },
        highlights=highlights or ["No significant highlights for this period."],
        risks=risks,
    )

    _store_snapshot(
        db,
        user_id=user_id,
        report_type="monthly_exec",
        period_key=month_key,
        data_json=report.model_dump(mode="json"),
    )
    return report


@router.get("/snapshots")
@limiter.limit("70/minute")
def list_snapshots(
    request: Request,
    report_type: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    del request
    user_id = _as_int(getattr(current_user, "id", 0))
    safe_limit = max(1, min(200, int(limit)))
    query = db.query(models.ReportSnapshot).filter(models.ReportSnapshot.user_id == user_id)
    if report_type:
        query = query.filter(models.ReportSnapshot.report_type == report_type)
    rows = query.order_by(models.ReportSnapshot.generated_at.desc()).limit(safe_limit).all()
    return [
        {
            "id": int(getattr(row, "id", 0)),
            "report_type": _as_str(getattr(row, "report_type", "")),
            "period_key": _as_str(getattr(row, "period_key", "")),
            "generated_at": str(getattr(row, "generated_at", "")),
            "exported_format": getattr(row, "exported_format", None),
        }
        for row in rows
    ]
