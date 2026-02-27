from fastapi import APIRouter, Depends, status, BackgroundTasks, Request
from sqlalchemy.orm import Session
from datetime import timedelta
import secrets

from ..database import get_db
from .. import schemas, crud, exceptions
from ..auth import create_access_token, create_refresh_token, SECRET_KEY, ALGORITHM, get_current_user
from ..logger import auth_logger, security_logger
from jose import jwt, JWTError
from datetime import datetime
from backend.core.limiter import limiter

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/login", response_model=schemas.TokenResponse)
@limiter.limit("5/minute")
def login(request: Request, data: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = crud.authenticate_user(db, data.email, data.password)

    if not user:
        auth_logger.warning(f"Failed login attempt: {data.email}")
        raise exceptions.AuthenticationError("Invalid email or password")

    if not user.is_verified:
        raise exceptions.AuthenticationError("Please verify your email address")

    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    # Store refresh token in DB
    crud.update_user(db, user.id, {"refresh_token": refresh_token})
    
    auth_logger.info(f"User logged in: {user.email}")
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user
    }

@router.post("/refresh", response_model=schemas.TokenResponse)
def refresh_token(payload: schemas.TokenRefreshRequest, db: Session = Depends(get_db)):
    try:
        data = jwt.decode(payload.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        if data.get("type") != "refresh":
            raise exceptions.AuthenticationError("Invalid refresh token")
            
        user_id = data.get("sub")
        user = crud.get_user(db, int(user_id))
        
        if not user or user.refresh_token != payload.refresh_token:
            security_logger.error(f"Potential token reuse/theft detected for user {user_id}")
            raise exceptions.AuthenticationError("Token invalid or expired")
            
        new_access = create_access_token({"sub": str(user.id)})
        return {
            "access_token": new_access,
            "refresh_token": user.refresh_token,
            "token_type": "bearer",
            "user": user
        }
    except JWTError:
        raise exceptions.AuthenticationError("Invalid refresh token")

@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=schemas.TokenResponse)
@limiter.limit("3/minute")
def register(request: Request, user: schemas.UserCreate, db: Session = Depends(get_db), background_tasks: BackgroundTasks = None):
    existing = crud.get_user_by_email(db, user.email)
    if existing:
        raise exceptions.ValidationError("Email already registered")
    
    db_user = crud.create_user(db, user)
    
    # Auto-verify user since there is no live email system in this environment
    crud.update_user(db, db_user.id, {"is_verified": True})
    db.refresh(db_user)

    # Issue tokens immediately so the frontend can log the user in right away
    access_token = create_access_token(data={"sub": str(db_user.id)})
    refresh_token = create_refresh_token(data={"sub": str(db_user.id)})
    crud.update_user(db, db_user.id, {"refresh_token": refresh_token})

    auth_logger.info(f"New user registered and auto-verified: {user.email}")
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": db_user
    }

@router.get("/verify-email")
def verify_email(token: str, db: Session = Depends(get_db)):
    user = db.query(crud.models.User).filter(crud.models.User.verification_token == token).first()
    if not user:
        raise exceptions.AuthenticationError("Invalid or expired verification token")
    
    user.is_verified = True
    user.verification_token = None
    db.commit()
    return {"message": "Email verified successfully"}

@router.post("/logout")
def logout(db: Session = Depends(get_db), current_user: crud.models.User = Depends(get_current_user)):
    crud.update_user(db, current_user.id, {"refresh_token": None})
    auth_logger.info(f"User logged out: {current_user.email}")
    return {"message": "Successfully logged out"}

@router.post("/request-password-reset")
def request_password_reset(data: schemas.PasswordResetRequest, db: Session = Depends(get_db)):
    user = crud.get_user_by_email(db, data.email)
    if user:
        reset_token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=1)
        crud.update_user(db, user.id, {
            "reset_password_token": reset_token,
            "reset_password_expires_at": expires_at
        })
        auth_logger.info(f"Password reset requested for {data.email}. Token: {reset_token}")
    
    return {"message": "If that email exists, a reset link has been sent."}

@router.post("/reset-password")
def reset_password(data: schemas.PasswordResetConfirm, db: Session = Depends(get_db)):
    user = db.query(crud.models.User).filter(
        crud.models.User.reset_password_token == data.token,
        crud.models.User.reset_password_expires_at > datetime.utcnow()
    ).first()
    
    if not user:
        raise exceptions.ValidationError("Invalid or expired reset token")
    
    from ..crud import pwd_context
    user.password = pwd_context.hash(data.new_password)
    user.reset_password_token = None
    user.reset_password_expires_at = None
    db.commit()
    auth_logger.info(f"Password reset successful for user {user.id}")
    return {"message": "Password reset successful"}

