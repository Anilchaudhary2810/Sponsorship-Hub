import json
import hmac
import hashlib
from datetime import datetime
from typing import Any, Optional
from fastapi import APIRouter, Depends, Request, Header
from sqlalchemy.orm import Session

# import razorpay # Not real for now, just change vendor

from ..database import get_db
from .. import models, schemas, exceptions, crud
from ..config import settings
from ..logger import payment_logger, security_logger
from ..auth import get_current_user
from backend.core.limiter import limiter

router = APIRouter(prefix="/payments", tags=["Payments"])

try:
    import razorpay  # type: ignore[import]
except Exception:  # pragma: no cover - optional dependency
    razorpay = None


def _to_str(value: object, default: str = "") -> str:
    return value if isinstance(value, str) else default


def _resolve_deal_id_from_provider_order(
    db: Session,
    order_entity: Optional[dict[str, Any]] = None,
    payment_entity: Optional[dict[str, Any]] = None,
) -> Optional[int]:
    if order_entity:
        notes = order_entity.get("notes", {})
        raw = notes.get("deal_id")
        if raw is not None:
            try:
                return int(raw)
            except (TypeError, ValueError):
                pass

    order_id = ""
    if payment_entity:
        order_id = _to_str(payment_entity.get("order_id"))
    if not order_id and order_entity:
        order_id = _to_str(order_entity.get("id"))

    if not order_id:
        return None

    deal = db.query(models.Deal).filter(models.Deal.razorpay_payment_id == order_id).first()
    if not deal:
        return None

    try:
        return int(getattr(deal, "id"))
    except (TypeError, ValueError):
        return None


def _create_provider_order_or_mock(
    *,
    deal_id: int,
    amount_paise: int,
    currency: str,
) -> str:
    key_id = settings.RAZORPAY_KEY_ID
    key_secret = settings.RAZORPAY_KEY_SECRET
    env = (settings.ENV or "").lower()

    if key_id and key_secret and razorpay is not None:
        try:
            client = razorpay.Client(auth=(key_id, key_secret))
            order = client.order.create(
                {
                    "amount": amount_paise,
                    "currency": currency,
                    "receipt": f"deal_{deal_id}",
                    "notes": {"deal_id": str(deal_id)},
                }
            )
            order_id = _to_str(order.get("id"))
            if not order_id:
                raise exceptions.PaymentError("Payment provider returned invalid order response")
            return order_id
        except Exception as exc:
            raise exceptions.PaymentError(f"Provider order creation failed: {exc}") from exc

    # In production, gateway keys + SDK are mandatory for real checkout.
    if env in {"production", "prod"}:
        raise exceptions.PaymentError("Payment gateway is not configured for production")

    # Development fallback so local UX remains testable without gateway creds.
    return f"order_{deal_id}_{int(datetime.utcnow().timestamp())}"


@router.get("/checkout-config", response_model=schemas.PaymentCheckoutConfigResponse)
@limiter.limit("80/minute")
async def get_checkout_config(
    request: Request,
    current_user: models.User = Depends(get_current_user),
):
    del request, current_user
    return schemas.PaymentCheckoutConfigResponse(
        provider="razorpay",
        key_id=settings.RAZORPAY_KEY_ID,
    )

@router.post("/create-order", response_model=schemas.DealResponse)
@limiter.limit("15/minute")
async def create_razorpay_order(
    request: Request,
    deal_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    deal = db.query(models.Deal).filter(models.Deal.id == deal_id).first()
    if not deal:
        raise exceptions.BusinessLogicError("Deal not found")

    deal_sponsor_id = int(getattr(deal, "sponsor_id", 0)) if getattr(deal, "sponsor_id", None) is not None else 0
    current_user_id = int(getattr(current_user, "id", 0))

    if deal_sponsor_id != current_user_id:
        raise exceptions.AuthorizationError("You can only pay for your own deals")

    if bool(getattr(deal, "payment_done", False)):
        raise exceptions.BusinessLogicError("Deal is already paid")

    # Check for existing order to ensure idempotency
    existing_payment_id = getattr(deal, "razorpay_payment_id", None)
    existing_payment_status = str(getattr(deal, "payment_status", ""))
    if isinstance(existing_payment_id, str) and existing_payment_id and existing_payment_status == "created":
        # In a real app, we might fetch from Razorpay here
        pass
    else:
        try:
            # Amount in paise (1 INR = 100 paise)
            deal_amount = float(getattr(deal, "payment_amount", 0) or 0)
            if deal_amount <= 0:
                raise exceptions.ValidationError("Deal amount must be greater than zero before creating payment order")
            amount = int(deal_amount * 100)
            
            order_id = _create_provider_order_or_mock(
                deal_id=int(getattr(deal, "id", deal_id)),
                amount_paise=amount,
                currency=_to_str(getattr(deal, "currency", "INR"), default="INR") or "INR",
            )

            setattr(deal, "razorpay_payment_id", order_id)
            setattr(deal, "payment_status", "created")
            db.commit()
            payment_logger.info(f"Created Razorpay Order {order_id} for Deal {deal.id}")
        except Exception as e:
            payment_logger.error(f"Razorpay Error: {str(e)}")
            raise exceptions.PaymentError(f"Razorpay system error: {str(e)}")

    db.refresh(deal)
    return deal

@router.post("/webhook")
@limiter.limit("120/minute")
async def razorpay_webhook(request: Request, x_razorpay_signature: str = Header(None), db: Session = Depends(get_db)):
    payload_body = await request.body()

    webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET
    env = (settings.ENV or "").lower()

    if webhook_secret:
        if not x_razorpay_signature:
            security_logger.error("Missing Razorpay webhook signature header")
            raise exceptions.ValidationError("Invalid signature")

        expected_signature = hmac.new(
            webhook_secret.encode("utf-8"),
            payload_body,
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(expected_signature, x_razorpay_signature):
            security_logger.error("Invalid Razorpay webhook signature")
            raise exceptions.ValidationError("Invalid signature")
    elif env in {"production", "prod"}:
        security_logger.error("Webhook secret is not configured in production")
        raise exceptions.ValidationError("Webhook configuration invalid")
    else:
        security_logger.warning("Webhook signature validation skipped (missing RAZORPAY_WEBHOOK_SECRET in non-production)")

    try:
        payload = json.loads(payload_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise exceptions.ValidationError("Invalid webhook payload")

    event = payload.get("event")

    payload_root = payload.get("payload", {})
    order_entity = payload_root.get("order", {}).get("entity", {})
    payment_entity = payload_root.get("payment", {}).get("entity", {})
    deal_id = _resolve_deal_id_from_provider_order(
        db,
        order_entity=order_entity if isinstance(order_entity, dict) else None,
        payment_entity=payment_entity if isinstance(payment_entity, dict) else None,
    )

    # Accept both order and payment capture events. Final settlement state
    # is still webhook-driven only.
    if event in {"order.paid", "payment.captured"} and deal_id is not None:
        provider_reference = _to_str(payment_entity.get("id")) or _to_str(order_entity.get("id"))
        if provider_reference:
            crud.deal_payment_webhook(db, int(deal_id), provider_reference, "succeeded")
    elif event in {"order.failed", "payment.failed"} and deal_id is not None:
        provider_reference = _to_str(payment_entity.get("id")) or _to_str(order_entity.get("id"))
        if provider_reference:
            crud.deal_payment_webhook(db, int(deal_id), provider_reference, "failed")

    return {"status": "success"}
