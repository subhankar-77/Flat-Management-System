"""
SQLAlchemy ORM models — one class = one PostgreSQL table.

Tables created:
  users              — admin accounts
  flats              — the 9 flats in the building
  flat_owners        — owner / tenant linked to a flat
  maintenance_charges— monthly charge records per flat
  payments           — every Razorpay transaction
  notices            — society notice board
"""

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey,
    Numeric, Text, Enum as SAEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.database import Base


# ── Enums ─────────────────────────────────────────────────────────────────────

class OwnershipType(str, enum.Enum):
    owner_occupied    = "owner_occupied"
    tenant            = "tenant"
    owner_not_residing = "owner_not_residing"


class PaymentStatus(str, enum.Enum):
    created   = "created"
    pending   = "pending"
    success   = "success"
    failed    = "failed"
    refunded  = "refunded"


class PaymentMethod(str, enum.Enum):
    upi         = "upi"
    card        = "card"
    net_banking = "net_banking"
    wallet      = "wallet"
    cash        = "cash"       # admin records offline cash payment


class MaintenanceStatus(str, enum.Enum):
    paid    = "paid"
    pending = "pending"
    overdue = "overdue"


class NoticeCategory(str, enum.Enum):
    general           = "general"
    maintenance       = "maintenance"
    payment_reminder  = "payment_reminder"
    emergency         = "emergency"
    event             = "event"


class NoticePriority(str, enum.Enum):
    low    = "low"
    medium = "medium"
    high   = "high"


# ── Tables ────────────────────────────────────────────────────────────────────

class User(Base):
    """Admin users who can log in to the dashboard."""
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    name          = Column(String(120), nullable=False)
    email         = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_admin      = Column(Boolean, default=True)
    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())


class Flat(Base):
    """One row per physical flat unit."""
    __tablename__ = "flats"

    id         = Column(Integer, primary_key=True, index=True)
    flat_number= Column(String(10), unique=True, nullable=False, index=True)  # e.g. "101"
    floor      = Column(String(50), nullable=False)                            # e.g. "1st Floor"
    area_sqft  = Column(Integer, nullable=True)
    is_active  = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    owner       = relationship("FlatOwner",        back_populates="flat",    uselist=False)
    maintenances= relationship("MaintenanceCharge", back_populates="flat")
    payments    = relationship("Payment",           back_populates="flat")


class FlatOwner(Base):
    """Owner or tenant currently associated with a flat."""
    __tablename__ = "flat_owners"

    id             = Column(Integer, primary_key=True, index=True)
    flat_id        = Column(Integer, ForeignKey("flats.id"), unique=True, nullable=False)
    full_name      = Column(String(150), nullable=False)
    email          = Column(String(255), nullable=True)
    phone          = Column(String(20),  nullable=True)
    alternate_phone= Column(String(20),  nullable=True)
    ownership_type = Column(
        SAEnum(OwnershipType, name="ownershiptype"),
        default=OwnershipType.owner_occupied,
        nullable=False
    )
    move_in_date   = Column(DateTime(timezone=True), nullable=True)
    notes          = Column(Text, nullable=True)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())
    updated_at     = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    flat = relationship("Flat", back_populates="owner")


class MaintenanceCharge(Base):
    """One record per flat per month — tracks what is owed and whether it's paid."""
    __tablename__ = "maintenance_charges"

    id            = Column(Integer, primary_key=True, index=True)
    flat_id       = Column(Integer, ForeignKey("flats.id"), nullable=False)
    month_year    = Column(String(20), nullable=False)   # e.g. "2025-05"
    amount        = Column(Numeric(10, 2), nullable=False)
    due_date      = Column(DateTime(timezone=True), nullable=True)
    status        = Column(
        SAEnum(MaintenanceStatus, name="maintenancestatus"),
        default=MaintenanceStatus.pending,
        nullable=False
    )
    late_fee      = Column(Numeric(10, 2), default=0)
    notes         = Column(Text, nullable=True)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    updated_at    = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    flat     = relationship("Flat",    back_populates="maintenances")
    payments = relationship("Payment", back_populates="maintenance_charge")


class Payment(Base):
    """Every Razorpay transaction (and admin-recorded cash payments)."""
    __tablename__ = "payments"

    id                    = Column(Integer, primary_key=True, index=True)
    flat_id               = Column(Integer, ForeignKey("flats.id"), nullable=False)
    maintenance_charge_id = Column(Integer, ForeignKey("maintenance_charges.id"), nullable=True)

    # Razorpay IDs
    razorpay_order_id    = Column(String(100), unique=True, nullable=True, index=True)
    razorpay_payment_id  = Column(String(100), unique=True, nullable=True, index=True)
    razorpay_signature   = Column(String(255), nullable=True)

    amount        = Column(Numeric(10, 2), nullable=False)   # in INR
    currency      = Column(String(5), default="INR")
    month_year    = Column(String(20), nullable=False)        # "2025-05"
    payment_method= Column(
        SAEnum(PaymentMethod, name="paymentmethod"),
        nullable=True
    )
    status        = Column(
        SAEnum(PaymentStatus, name="paymentstatus"),
        default=PaymentStatus.created,
        nullable=False
    )
    paid_at       = Column(DateTime(timezone=True), nullable=True)
    notes         = Column(Text, nullable=True)
    bill_photo_path = Column(String(500), nullable=True)   # stores file path
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    updated_at    = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    flat               = relationship("Flat",              back_populates="payments")
    maintenance_charge = relationship("MaintenanceCharge", back_populates="payments")


class Notice(Base):
    """Society notice board entries."""
    __tablename__ = "notices"

    id         = Column(Integer, primary_key=True, index=True)
    title      = Column(String(255), nullable=False)
    body       = Column(Text, nullable=False)
    category   = Column(
        SAEnum(NoticeCategory, name="noticecategory"),
        default=NoticeCategory.general,
        nullable=False
    )
    priority   = Column(
        SAEnum(NoticePriority, name="noticepriority"),
        default=NoticePriority.medium,
        nullable=False
    )
    posted_by  = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_active  = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
