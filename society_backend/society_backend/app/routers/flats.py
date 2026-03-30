from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List

from app.database import get_db
from app.models.models import Flat
from app.schemas.schemas import FlatCreate, FlatUpdate, FlatOut
from app.auth import require_admin

router = APIRouter()


@router.get("/", response_model=List[FlatOut])
def list_flats(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    """Return all flats with their current owner loaded."""
    return (
        db.query(Flat)
        .options(joinedload(Flat.owner))
        .filter(Flat.is_active == True)
        .offset(skip).limit(limit)
        .all()
    )


@router.get("/{flat_id}", response_model=FlatOut)
def get_flat(flat_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    flat = db.query(Flat).options(joinedload(Flat.owner)).filter(Flat.id == flat_id).first()
    if not flat:
        raise HTTPException(404, "Flat not found")
    return flat


@router.post("/", response_model=FlatOut, status_code=201)
def create_flat(payload: FlatCreate, db: Session = Depends(get_db), _=Depends(require_admin)):
    # Prevent duplicate flat numbers
    existing = db.query(Flat).filter(Flat.flat_number == payload.flat_number).first()
    if existing:
        raise HTTPException(400, f"Flat {payload.flat_number} already exists")

    flat = Flat(**payload.model_dump())
    db.add(flat)
    db.commit()
    db.refresh(flat)
    return flat


@router.put("/{flat_id}", response_model=FlatOut)
def update_flat(
    flat_id: int,
    payload: FlatUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    flat = db.query(Flat).filter(Flat.id == flat_id).first()
    if not flat:
        raise HTTPException(404, "Flat not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(flat, field, value)

    db.commit()
    db.refresh(flat)
    return flat


@router.delete("/{flat_id}", status_code=204)
def delete_flat(flat_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    flat = db.query(Flat).filter(Flat.id == flat_id).first()
    if not flat:
        raise HTTPException(404, "Flat not found")
    # Soft delete — keeps payment history intact
    flat.is_active = False
    db.commit()
