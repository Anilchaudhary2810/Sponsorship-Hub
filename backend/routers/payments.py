import json
import hmac
import hashlib
from datetime import datetime
from fastapi import APIRouter, Depends, Request, Header, BackgroundTasks
from sqlalchemy.orm import Session

# import razorpay # Not real for now, just change vendor

from ..database import get_db
from .. import models, schemas, exceptions, crud
from ..config import settings
from ..logger import payment_logger, security_logger
from ..auth import get_current_user
from backend.core.limiter import limiter

router = APIRouter(prefix="/payments", tags=["Payments"])

# razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

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
            amount = int(float(getattr(deal, "payment_amount", 0)) * 100)
            
            # Simulate Razorpay Order Creation
            # order = razorpay_client.order.create({
            #     "amount": amount,
            #     "currency": deal.currency,
            #     "receipt": f"deal_{deal.id}",
            #     "notes": {"deal_id": deal.id}
            # })
            
            # Mocking order ID for now
            mock_order_id = f"order_{deal.id}_{int(datetime.utcnow().timestamp())}"

            setattr(deal, "razorpay_payment_id", mock_order_id)
            setattr(deal, "payment_status", "created")
            db.commit()
            payment_logger.info(f"Created Razorpay Order {mock_order_id} for Deal {deal.id}")
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

    # Handle the event (simplified Razorpay event structure)
    if event == 'order.paid':
        order_entity = payload['payload']['order']['entity']
        notes = order_entity.get('notes', {})
        deal_id = notes.get('deal_id')
        if deal_id:
            crud.deal_payment_webhook(db, int(deal_id), order_entity['id'], "succeeded")

    elif event == 'order.failed':
        order_entity = payload['payload']['order']['entity']
        notes = order_entity.get('notes', {})
        deal_id = notes.get('deal_id')
        if deal_id:
            crud.deal_payment_webhook(db, int(deal_id), order_entity['id'], "failed")

    return {"status": "success"}
