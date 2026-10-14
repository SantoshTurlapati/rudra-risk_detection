import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.v1.deps import get_db, get_current_user
from app.db.models import User, Organization
from app.core.security import verify_password, get_password_hash, create_access_token
from app.schemas.all_schemas import (
    UserLogin, UserCreate, UserResponse, Token,
    PasswordResetRequest, PasswordResetConfirm
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=Token)
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    # Find user by email or username
    user = db.query(User).filter(
        (User.email == login_data.username_or_email) |
        (User.username == login_data.username_or_email)
    ).first()

    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email/username or password."
        )

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Account is disabled.")

    access_token = create_access_token(subject=user.id)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role,
            "organization_id": user.organization_id,
            "avatar_url": user.avatar_url
        }
    }

@router.post("/register", response_model=UserResponse)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    # Check if email exists
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="A user with this email already exists.")

    # Create default organization if needed
    org = Organization(
        name=user_in.organization_name or "RudraShield Organization",
        slug=f"org-{uuid.uuid4().hex[:8]}"
    )
    db.add(org)
    db.flush()

    user = User(
        organization_id=org.id,
        email=user_in.email,
        username=user_in.username or user_in.email.split('@')[0],
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        role="analyst"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/logout")
def logout():
    return {"message": "Clear the locally stored access token to sign out."}

@router.post("/forgot-password")
def forgot_password(req: PasswordResetRequest):
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Password recovery is unavailable until secure token delivery is configured."
    )

@router.post("/reset-password")
def reset_password(req: PasswordResetConfirm):
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Password recovery is unavailable until secure token validation and delivery are configured."
    )
