from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.models import Notice, User
from app.schemas.schemas import NoticeCreate, NoticeUpdate, NoticeOut
from app.auth import require_admin, get_current_user

router = APIRouter()


@router.get("/", response_model=List[NoticeOut])
def list_notices(
    active_only: bool = True,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    q = db.query(Notice)
    if active_only:
        q = q.filter(Notice.is_active == True)
    return q.order_by(Notice.created_at.desc()).all()


@router.get("/{notice_id}", response_model=NoticeOut)
def get_notice(notice_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    notice = db.query(Notice).filter(Notice.id == notice_id).first()
    if not notice:
        raise HTTPException(404, "Notice not found")
    return notice


@router.post("/", response_model=NoticeOut, status_code=201)
def create_notice(
    payload: NoticeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    notice = Notice(**payload.model_dump(), posted_by=current_user.id)
    db.add(notice)
    db.commit()
    db.refresh(notice)
    return notice


@router.put("/{notice_id}", response_model=NoticeOut)
def update_notice(
    notice_id: int,
    payload: NoticeUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    notice = db.query(Notice).filter(Notice.id == notice_id).first()
    if not notice:
        raise HTTPException(404, "Notice not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(notice, field, value)

    db.commit()
    db.refresh(notice)
    return notice


@router.delete("/{notice_id}", status_code=204)
def delete_notice(notice_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    notice = db.query(Notice).filter(Notice.id == notice_id).first()
    if not notice:
        raise HTTPException(404, "Notice not found")
    db.delete(notice)
    db.commit()
