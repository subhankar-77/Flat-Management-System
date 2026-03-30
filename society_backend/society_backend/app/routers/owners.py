from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.models import FlatOwner, Flat
from app.schemas.schemas import FlatOwnerCreate, FlatOwnerUpdate, FlatOwnerOut
from app.auth import require_admin

router = APIRouter()


@router.get("/", response_model=List[FlatOwnerOut])
def list_owners(db: Session = Depends(get_db), _=Depends(require_admin)):
    return db.query(FlatOwner).all()


@router.get("/{owner_id}", response_model=FlatOwnerOut)
def get_owner(owner_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    owner = db.query(FlatOwner).filter(FlatOwner.id == owner_id).first()
    if not owner:
        raise HTTPException(404, "Owner not found")
    return owner


@router.post("/", response_model=FlatOwnerOut, status_code=201)
def create_owner(payload: FlatOwnerCreate, db: Session = Depends(get_db), _=Depends(require_admin)):
    # Flat must exist
    flat = db.query(Flat).filter(Flat.id == payload.flat_id, Flat.is_active == True).first()
    if not flat:
        raise HTTPException(404, "Flat not found")

    # Each flat can have only one active owner record
    existing = db.query(FlatOwner).filter(FlatOwner.flat_id == payload.flat_id).first()
    if existing:
        raise HTTPException(400, f"Flat {flat.flat_number} already has an owner. Update the existing record instead.")

    owner = FlatOwner(**payload.model_dump())
    db.add(owner)
    db.commit()
    db.refresh(owner)
    return owner


@router.put("/{owner_id}", response_model=FlatOwnerOut)
def update_owner(
    owner_id: int,
    payload: FlatOwnerUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    owner = db.query(FlatOwner).filter(FlatOwner.id == owner_id).first()
    if not owner:
        raise HTTPException(404, "Owner not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(owner, field, value)

    db.commit()
    db.refresh(owner)
    return owner


@router.delete("/{owner_id}", status_code=204)
def delete_owner(owner_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    owner = db.query(FlatOwner).filter(FlatOwner.id == owner_id).first()
    if not owner:
        raise HTTPException(404, "Owner not found")
    db.delete(owner)
    db.commit()
