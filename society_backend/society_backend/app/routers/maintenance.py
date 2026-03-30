from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List

from app.database import get_db
from app.models.models import MaintenanceCharge, Flat, MaintenanceStatus
from app.schemas.schemas import (
    MaintenanceCreate, MaintenanceUpdate, MaintenanceOut, BulkMaintenanceCreate
)
from app.auth import require_admin
from app.config import settings

router = APIRouter()


@router.get("/", response_model=List[MaintenanceOut])
def list_charges(
    month_year: str = None,
    flat_id: int = None,
    status: MaintenanceStatus = None,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    """
    List maintenance charges. Filter by month_year (e.g. '2025-05'),
    flat_id, or status (paid/pending/overdue).
    """
    q = db.query(MaintenanceCharge).options(joinedload(MaintenanceCharge.flat))
    if month_year:
        q = q.filter(MaintenanceCharge.month_year == month_year)
    if flat_id:
        q = q.filter(MaintenanceCharge.flat_id == flat_id)
    if status:
        q = q.filter(MaintenanceCharge.status == status)
    return q.order_by(MaintenanceCharge.month_year.desc()).all()


@router.get("/{charge_id}", response_model=MaintenanceOut)
def get_charge(charge_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    charge = db.query(MaintenanceCharge).filter(MaintenanceCharge.id == charge_id).first()
    if not charge:
        raise HTTPException(404, "Charge not found")
    return charge


@router.post("/", response_model=MaintenanceOut, status_code=201)
def create_charge(
    payload: MaintenanceCreate,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    """Create a maintenance charge for a single flat for a given month."""
    flat = db.query(Flat).filter(Flat.id == payload.flat_id, Flat.is_active == True).first()
    if not flat:
        raise HTTPException(404, "Flat not found")

    # Prevent duplicates for the same flat + month
    dup = db.query(MaintenanceCharge).filter(
        MaintenanceCharge.flat_id == payload.flat_id,
        MaintenanceCharge.month_year == payload.month_year
    ).first()
    if dup:
        raise HTTPException(400, f"Charge for Flat {flat.flat_number} in {payload.month_year} already exists")

    charge = MaintenanceCharge(**payload.model_dump())
    db.add(charge)
    db.commit()
    db.refresh(charge)
    return charge


@router.post("/bulk", status_code=201)
def bulk_create_charges(
    payload: BulkMaintenanceCreate,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    """
    Create maintenance charges for ALL active flats in one shot.
    Use at the start of each month. Skips flats that already have a charge
    for the given month.
    """
    active_flats = db.query(Flat).filter(Flat.is_active == True).all()
    created = []
    skipped = []

    for flat in active_flats:
        existing = db.query(MaintenanceCharge).filter(
            MaintenanceCharge.flat_id == flat.id,
            MaintenanceCharge.month_year == payload.month_year
        ).first()
        if existing:
            skipped.append(flat.flat_number)
            continue

        charge = MaintenanceCharge(
            flat_id=flat.id,
            month_year=payload.month_year,
            amount=payload.amount,
            due_date=payload.due_date,
        )
        db.add(charge)
        created.append(flat.flat_number)

    db.commit()
    return {
        "message": f"Bulk charges created for {payload.month_year}",
        "created_for_flats": created,
        "skipped_flats": skipped,
    }


@router.put("/{charge_id}", response_model=MaintenanceOut)
def update_charge(
    charge_id: int,
    payload: MaintenanceUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    charge = db.query(MaintenanceCharge).filter(MaintenanceCharge.id == charge_id).first()
    if not charge:
        raise HTTPException(404, "Charge not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(charge, field, value)

    db.commit()
    db.refresh(charge)
    return charge


@router.delete("/{charge_id}", status_code=204)
def delete_charge(charge_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    charge = db.query(MaintenanceCharge).filter(MaintenanceCharge.id == charge_id).first()
    if not charge:
        raise HTTPException(404, "Charge not found")
    db.delete(charge)
    db.commit()


@router.get("/summary/{month_year}")
def monthly_summary(month_year: str, db: Session = Depends(get_db), _=Depends(require_admin)):
    """Dashboard summary for a specific month (e.g. '2025-05')."""
    from decimal import Decimal

    charges = db.query(MaintenanceCharge).filter(
        MaintenanceCharge.month_year == month_year
    ).all()

    total_flats    = db.query(Flat).filter(Flat.is_active == True).count()
    paid           = [c for c in charges if c.status == MaintenanceStatus.paid]
    pending        = [c for c in charges if c.status == MaintenanceStatus.pending]
    overdue        = [c for c in charges if c.status == MaintenanceStatus.overdue]
    collected      = sum(c.amount for c in paid)
    outstanding    = sum(c.amount for c in pending + overdue)
    rate           = round(len(paid) / total_flats * 100, 1) if total_flats else 0

    return {
        "month_year":               month_year,
        "total_flats":              total_flats,
        "paid_count":               len(paid),
        "pending_count":            len(pending),
        "overdue_count":            len(overdue),
        "total_collected":          str(collected),
        "total_outstanding":        str(outstanding),
        "collection_rate_percent":  rate,
    }
