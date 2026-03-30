from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import User
from app.schemas.schemas import LoginRequest, Token, UserOut
from app.auth import verify_password, create_access_token, hash_password, get_current_user
from app.config import settings

router = APIRouter()


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Exchange email + password for a JWT access token.
    Use the token as: Authorization: Bearer <token>
    """
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated admin's profile."""
    return current_user


@router.post("/seed-admin", include_in_schema=False)
def seed_admin(db: Session = Depends(get_db)):
    """
    One-time endpoint to create the initial admin account.
    Run once, then REMOVE or DISABLE this endpoint in production.
    Credentials come from .env → ADMIN_EMAIL / ADMIN_PASSWORD.
    """
    existing = db.query(User).filter(User.email == settings.ADMIN_EMAIL).first()
    if existing:
        return {"message": "Admin already exists"}

    admin = User(
        name=settings.ADMIN_NAME,
        email=settings.ADMIN_EMAIL,
        hashed_password=hash_password(settings.ADMIN_PASSWORD),
        is_admin=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return {"message": f"Admin created: {admin.email}"}
