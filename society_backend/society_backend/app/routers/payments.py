"""
Payment flow (Razorpay):

  1.  Admin selects flat → POST /api/payments/create-order
      → We create a Razorpay order + a Payment row (status=created)
      → Return razorpay_order_id + key_id to the frontend

  2.  Frontend opens Razorpay checkout modal with the order_id.
      Owner pays via UPI / card / net banking.

  3.  Razorpay redirects back → Frontend POSTs to /api/payments/verify
      → We verify the HMAC signature to confirm the payment is genuine
      → Update Payment row to status=success
      → Mark the linked MaintenanceCharge as paid

  4.  (Optional) Razorpay Webhook → POST /api/payments/webhook
      Server-side confirmation for reliability (even if browser closes).
"""

import hmac
import hashlib
import razorpay
from datetime import datetime, timezone
from decimal import Decimal


from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Header, UploadFile, File
from app.database import get_db
from app.models.models import Payment, Flat, MaintenanceCharge, PaymentStatus, PaymentMethod, MaintenanceStatus
from app.schemas.schemas import (
    CreateOrderRequest, CreateOrderResponse,
    VerifyPaymentRequest, RecordCashPaymentRequest, PaymentOut
)
from app.auth import require_admin
from app.config import settings

import os, shutil

from fastapi.responses import FileResponse

router = APIRouter()


def get_razorpay_client():
    return razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )


# ── Create Razorpay Order ─────────────────────────────────────────────────────

@router.post("/create-order", response_model=CreateOrderResponse)
def create_order(
    payload: CreateOrderRequest,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    """
    Step 1: Create a Razorpay order.
    Returns order details the frontend needs to open the checkout modal.
    """
    flat = db.query(Flat).filter(Flat.id == payload.flat_id, Flat.is_active == True).first()
    if not flat:
        raise HTTPException(404, "Flat not found")

    rz = get_razorpay_client()

    # Razorpay expects amount in paise (1 INR = 100 paise)
    amount_paise = int(payload.amount * 100)

    rz_order = rz.order.create({
        "amount":   amount_paise,
        "currency": "INR",
        "notes": {
            "flat_number": flat.flat_number,
            "month_year":  payload.month_year,
            "society":     settings.SOCIETY_NAME,
        }
    })

    # Save payment row in DB (status=created until verified)
    payment = Payment(
        flat_id=payload.flat_id,
        maintenance_charge_id=payload.maintenance_charge_id,
        razorpay_order_id=rz_order["id"],
        amount=payload.amount,
        currency="INR",
        month_year=payload.month_year,
        notes=payload.notes,
        status=PaymentStatus.created,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    return CreateOrderResponse(
        payment_id=payment.id,
        razorpay_order_id=rz_order["id"],
        amount=amount_paise,
        currency="INR",
        key_id=settings.RAZORPAY_KEY_ID,
    )


# ── Verify Payment (after checkout modal closes) ──────────────────────────────

@router.post("/verify")
def verify_payment(
    payload: VerifyPaymentRequest,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    """
    Step 2: Verify the HMAC signature Razorpay sends after a successful payment.
    This is the SECURITY CRITICAL step — do not skip it.
    """
    # HMAC verification
    expected = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode(),
        f"{payload.razorpay_order_id}|{payload.razorpay_payment_id}".encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, payload.razorpay_signature):
        raise HTTPException(400, "Invalid payment signature — payment not verified")

    # Update payment row
    payment = db.query(Payment).filter(
        Payment.razorpay_order_id == payload.razorpay_order_id
    ).first()
    if not payment:
        raise HTTPException(404, "Payment record not found")

    payment.razorpay_payment_id = payload.razorpay_payment_id
    payment.razorpay_signature  = payload.razorpay_signature
    payment.status              = PaymentStatus.success
    payment.paid_at             = datetime.now(timezone.utc)

    # Fetch method from Razorpay
    try:
        rz = get_razorpay_client()
        rz_payment = rz.payment.fetch(payload.razorpay_payment_id)
        method_map = {
            "upi": PaymentMethod.upi,
            "card": PaymentMethod.card,
            "netbanking": PaymentMethod.net_banking,
            "wallet": PaymentMethod.wallet,
        }
        payment.payment_method = method_map.get(rz_payment.get("method"), None)
    except Exception:
        pass  # Non-fatal — method can be filled in manually

    # Mark the linked maintenance charge as paid
    if payment.maintenance_charge_id:
        charge = db.query(MaintenanceCharge).filter(
            MaintenanceCharge.id == payment.maintenance_charge_id
        ).first()
        if charge:
            charge.status = MaintenanceStatus.paid

    db.commit()
    return {"message": "Payment verified and recorded successfully", "payment_id": payment.id}


# ── Razorpay Webhook (server-side event) ─────────────────────────────────────

@router.post("/webhook")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """
    Razorpay calls this URL when a payment event occurs (even if the user
    closes the browser). Configure this URL in:
    Razorpay Dashboard → Settings → Webhooks → Add Webhook URL
    Secret: same as RAZORPAY_KEY_SECRET
    """
    body = await request.body()

    # Verify webhook signature
    expected = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, x_razorpay_signature or ""):
        raise HTTPException(400, "Invalid webhook signature")

    import json
    event = json.loads(body)

    if event.get("event") == "payment.captured":
        rz_payment = event["payload"]["payment"]["entity"]
        order_id   = rz_payment.get("order_id")
        payment_id = rz_payment.get("id")

        payment = db.query(Payment).filter(
            Payment.razorpay_order_id == order_id
        ).first()

        if payment and payment.status != PaymentStatus.success:
            payment.razorpay_payment_id = payment_id
            payment.status  = PaymentStatus.success
            payment.paid_at = datetime.now(timezone.utc)

            if payment.maintenance_charge_id:
                charge = db.query(MaintenanceCharge).filter(
                    MaintenanceCharge.id == payment.maintenance_charge_id
                ).first()
                if charge:
                    charge.status = MaintenanceStatus.paid

            db.commit()

    return {"status": "ok"}


# ── Record Cash Payment ───────────────────────────────────────────────────────

@router.post("/record-cash", response_model=PaymentOut)
def record_cash_payment(
    payload: RecordCashPaymentRequest,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    """Admin manually records a cash payment collected offline."""
    flat = db.query(Flat).filter(Flat.id == payload.flat_id, Flat.is_active == True).first()
    if not flat:
        raise HTTPException(404, "Flat not found")

    payment = Payment(
        flat_id=payload.flat_id,
        maintenance_charge_id=payload.maintenance_charge_id,
        amount=payload.amount,
        currency="INR",
        month_year=payload.month_year,
        payment_method=PaymentMethod.cash,
        status=PaymentStatus.success,
        paid_at=datetime.now(timezone.utc),
        notes=payload.notes,
    )
    db.add(payment)

    if payload.maintenance_charge_id:
        charge = db.query(MaintenanceCharge).filter(
            MaintenanceCharge.id == payload.maintenance_charge_id
        ).first()
        if charge:
            charge.status = MaintenanceStatus.paid

    db.commit()
    db.refresh(payment)
    return payment


# ── List / Get Payments ───────────────────────────────────────────────────────

@router.get("/", response_model=List[PaymentOut])
def list_payments(
    flat_id: Optional[int] = None,
    month_year: Optional[str] = None,
    status: Optional[PaymentStatus] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    q = db.query(Payment).options(joinedload(Payment.flat))
    if flat_id:
        q = q.filter(Payment.flat_id == flat_id)
    if month_year:
        q = q.filter(Payment.month_year == month_year)
    if status:
        q = q.filter(Payment.status == status)
    return q.order_by(Payment.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/{payment_id}", response_model=PaymentOut)
def get_payment(payment_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    payment = db.query(Payment).options(joinedload(Payment.flat)).filter(
        Payment.id == payment_id
    ).first()
    if not payment:
        raise HTTPException(404, "Payment not found")
    return payment
