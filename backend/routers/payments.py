import json
from datetime import datetime
from fastapi import APIRouter, Depends, Request, Header, BackgroundTasks
from sqlalchemy.orm import Session

# import razorpay # Not real for now, just change vendor

from ..database import get_db
from .. import models, schemas, exceptions, crud
from ..config import settings
from ..logger import payment_logger, security_logger
from ..auth import get_current_user

router = APIRouter(prefix="/payments", tags=["Payments"])

# razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

@router.post("/create-order", response_model=schemas.DealResponse)
async def create_razorpay_order(
    deal_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    deal = db.query(models.Deal).filter(models.Deal.id == deal_id).first()
    if not deal:
        raise exceptions.BusinessLogicError("Deal not found")
        
    if deal.sponsor_id != current_user.id:
        raise exceptions.AuthorizationError("You can only pay for your own deals")
        
    if deal.payment_done:
        raise exceptions.BusinessLogicError("Deal is already paid")

    # Check for existing order to ensure idempotency
    if deal.razorpay_payment_id and deal.payment_status == "created":
        # In a real app, we might fetch from Razorpay here
        pass
    else:
        try:
            # Amount in paise (1 INR = 100 paise)
            amount = int(deal.payment_amount * 100)
            
            # Simulate Razorpay Order Creation
            # order = razorpay_client.order.create({
            #     "amount": amount,
            #     "currency": deal.currency,
            #     "receipt": f"deal_{deal.id}",
            #     "notes": {"deal_id": deal.id}
            # })
            
            # Mocking order ID for now
            mock_order_id = f"order_{deal.id}_{int(datetime.utcnow().timestamp())}"
            
            deal.razorpay_payment_id = mock_order_id
            deal.payment_status = "created"
            db.commit()
            payment_logger.info(f"Created Razorpay Order {mock_order_id} for Deal {deal.id}")
        except Exception as e:
            payment_logger.error(f"Razorpay Error: {str(e)}")
            raise exceptions.PaymentError(f"Razorpay system error: {str(e)}")

    db.refresh(deal)
    return deal

@router.post("/webhook")
async def razorpay_webhook(request: Request, x_razorpay_signature: str = Header(None), db: Session = Depends(get_db)):
    payload_body = await request.body()
    
    # In a real app, verify signature:
    # try:
    #     razorpay_client.utility.verify_webhook_signature(payload_body, x_razorpay_signature, settings.RAZORPAY_WEBHOOK_SECRET)
    # except Exception:
    #     security_logger.error("Invalid Razorpay webhook signature")
    #     raise exceptions.ValidationError("Invalid signature")

    payload = json.loads(payload_body)
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
