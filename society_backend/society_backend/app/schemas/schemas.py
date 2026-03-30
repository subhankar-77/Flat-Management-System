"""
Pydantic schemas — validate incoming request bodies and shape API responses.
Every router imports its schemas from here.
"""

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from app.models.models import (
    OwnershipType, PaymentStatus, PaymentMethod,
    MaintenanceStatus, NoticeCategory, NoticePriority
)


# ── Auth ──────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserOut(BaseModel):
    id: int
    name: str
    email: str
    is_admin: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── Flat ──────────────────────────────────────────────────────────────────────

class FlatBase(BaseModel):
    flat_number: str = Field(..., max_length=10, examples=["101"])
    floor: str       = Field(..., examples=["Ground Floor"])
    area_sqft: Optional[int] = None

class FlatCreate(FlatBase):
    pass

class FlatUpdate(BaseModel):
    flat_number: Optional[str] = None
    floor: Optional[str] = None
    area_sqft: Optional[int] = None
    is_active: Optional[bool] = None

class FlatOut(FlatBase):
    id: int
    is_active: bool
    created_at: datetime
    owner: Optional["FlatOwnerOut"] = None

    class Config:
        from_attributes = True


# ── Flat Owner ────────────────────────────────────────────────────────────────

class FlatOwnerBase(BaseModel):
    full_name: str       = Field(..., max_length=150)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    alternate_phone: Optional[str] = Field(None, max_length=20)
    ownership_type: OwnershipType = OwnershipType.owner_occupied
    move_in_date: Optional[datetime] = None
    notes: Optional[str] = None

class FlatOwnerCreate(FlatOwnerBase):
    flat_id: int

class FlatOwnerUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    alternate_phone: Optional[str] = None
    ownership_type: Optional[OwnershipType] = None
    move_in_date: Optional[datetime] = None
    notes: Optional[str] = None

class FlatOwnerOut(FlatOwnerBase):
    id: int
    flat_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Resolve forward reference
FlatOut.model_rebuild()


# ── Maintenance Charge ────────────────────────────────────────────────────────

class MaintenanceCreate(BaseModel):
    flat_id: int
    month_year: str    = Field(..., examples=["2025-05"])
    amount: Decimal    = Field(..., gt=0)
    due_date: Optional[datetime] = None
    late_fee: Decimal  = Decimal("0")
    notes: Optional[str] = None

class MaintenanceUpdate(BaseModel):
    amount: Optional[Decimal] = None
    due_date: Optional[datetime] = None
    status: Optional[MaintenanceStatus] = None
    late_fee: Optional[Decimal] = None
    notes: Optional[str] = None

class MaintenanceOut(BaseModel):
    id: int
    flat_id: int
    month_year: str
    amount: Decimal
    due_date: Optional[datetime] = None
    status: MaintenanceStatus
    late_fee: Decimal
    notes: Optional[str] = None
    created_at: datetime
    flat: Optional[FlatOut] = None

    class Config:
        from_attributes = True


# Bulk create maintenance charges for all flats in a given month
class BulkMaintenanceCreate(BaseModel):
    month_year: str    = Field(..., examples=["2025-06"])
    amount: Decimal    = Field(..., gt=0)
    due_date: Optional[datetime] = None


# ── Payment ───────────────────────────────────────────────────────────────────

class CreateOrderRequest(BaseModel):
    """Admin creates a Razorpay order before the owner pays."""
    flat_id: int
    maintenance_charge_id: Optional[int] = None
    month_year: str
    amount: Decimal = Field(..., gt=0)
    notes: Optional[str] = None

class CreateOrderResponse(BaseModel):
    payment_id: int             # our internal DB id
    razorpay_order_id: str
    amount: int                 # in paise (₹1 = 100 paise)
    currency: str
    key_id: str                 # Razorpay key to pass to frontend

class VerifyPaymentRequest(BaseModel):
    """Sent by frontend after Razorpay modal closes successfully."""
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str

class RecordCashPaymentRequest(BaseModel):
    """Admin records a cash payment offline."""
    flat_id: int
    maintenance_charge_id: Optional[int] = None
    month_year: str
    amount: Decimal
    notes: Optional[str] = None

class PaymentOut(BaseModel):
    id: int
    flat_id: int
    maintenance_charge_id: Optional[int] = None
    razorpay_order_id: Optional[str] = None
    razorpay_payment_id: Optional[str] = None
    amount: Decimal
    currency: str
    month_year: str
    payment_method: Optional[PaymentMethod] = None
    status: PaymentStatus
    paid_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime
    flat: Optional[FlatOut] = None

    class Config:
        from_attributes = True


# ── Notice ────────────────────────────────────────────────────────────────────

class NoticeCreate(BaseModel):
    title: str              = Field(..., max_length=255)
    body: str
    category: NoticeCategory = NoticeCategory.general
    priority: NoticePriority = NoticePriority.medium

class NoticeUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    category: Optional[NoticeCategory] = None
    priority: Optional[NoticePriority] = None
    is_active: Optional[bool] = None

class NoticeOut(BaseModel):
    id: int
    title: str
    body: str
    category: NoticeCategory
    priority: NoticePriority
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ── Dashboard Summary ─────────────────────────────────────────────────────────

class DashboardSummary(BaseModel):
    total_flats: int
    paid_this_month: int
    pending_this_month: int
    overdue_this_month: int
    total_collected_month: Decimal
    total_outstanding_month: Decimal
    collection_rate_percent: float
