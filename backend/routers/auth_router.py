from datetime import timedelta, datetime
import secrets
import os
from urllib.parse import quote

from fastapi import APIRouter, Depends, status, Request, Response, HTTPException
from sqlalchemy.orm import Session
from jose import JWTError

from ..database import get_db
from .. import schemas, crud, exceptions
from ..auth import (
    create_access_token,
    create_refresh_token,
    decode_token_sub,
    hash_token,
    get_current_user,
)
from ..config import settings
from ..logger import auth_logger, security_logger
from ..core.audit import log_audit_event
from ..core.email import send_password_reset_email
from backend.core.limiter import limiter

router = APIRouter(prefix="/auth", tags=["Auth"])


def _as_int(value: object, default: int = 0) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _as_str(value: object, default: str = "") -> str:
    if isinstance(value, str):
        return value
    return default


def _as_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    return default


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _user_agent(request: Request) -> str:
    return request.headers.get("user-agent", "")


def _should_send_password_reset_email() -> bool:
    env_value = (settings.ENV or "").lower()
    if env_value in {"test", "testing"}:
        return False
    if os.getenv("PYTEST_CURRENT_TEST"):
        return False
    return True


def _build_password_reset_link(raw_token: str) -> str:
    base = (settings.FRONTEND_BASE_URL or "").strip().rstrip("/")
    if not base:
        base = "http://localhost:5173"
    token_q = quote(raw_token, safe="")
    return f"{base}/reset-password?token={token_q}"


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str, csrf_token: str) -> None:
    is_prod = (settings.ENV or "").lower() in {"production", "prod"}
    cookie_secure = bool(is_prod)
    cookie_samesite = "none" if is_prod else "lax"

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite=cookie_samesite,
        secure=cookie_secure,
        max_age=60 * 60,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite=cookie_samesite,
        secure=cookie_secure,
        max_age=60 * 60 * 24 * 7,
        path="/",
    )
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=False,
        samesite=cookie_samesite,
        secure=cookie_secure,
        max_age=60 * 60 * 24 * 7,
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    response.delete_cookie("csrf_token", path="/")


@router.post("/login", response_model=schemas.AuthSessionResponse)
@limiter.limit("5/minute")
def login(request: Request, response: Response, data: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = crud.authenticate_user(db, data.email, data.password)

    if not user:
        auth_logger.warning(f"Failed login attempt: {data.email}")
        log_audit_event(
            db,
            action="auth.login_failed",
            target_type="user_email",
            target_id=None,
            ip_address=_client_ip(request),
            user_agent=_user_agent(request),
            metadata={"email": data.email},
        )
        raise exceptions.AuthenticationError("Invalid email or password")

    user_is_verified = _as_bool(getattr(user, "is_verified", False))
    if not user_is_verified:
        log_audit_event(
            db,
            action="auth.login_unverified",
            actor_user_id=_as_int(getattr(user, "id", 0), 0),
            target_type="user",
            target_id=_as_int(getattr(user, "id", 0), 0),
            ip_address=_client_ip(request),
            user_agent=_user_agent(request),
        )
        raise exceptions.AuthenticationError("Please verify your email address")

    user_id = _as_int(getattr(user, "id", 0))
    access_token = create_access_token(data={"sub": str(user_id)})
    refresh_token = create_refresh_token(data={"sub": str(user_id)})
    csrf_token = secrets.token_urlsafe(32)

    crud.update_user(db, user_id, {"refresh_token": hash_token(refresh_token)})
    _set_auth_cookies(response, access_token, refresh_token, csrf_token)

    auth_logger.info(f"User logged in: {_as_str(getattr(user, 'email', ''))}")
    log_audit_event(
        db,
        action="auth.login_success",
        actor_user_id=user_id,
        target_type="user",
        target_id=user_id,
        ip_address=_client_ip(request),
        user_agent=_user_agent(request),
    )
    return {
        "token_type": "bearer",
        "user": user,
        "message": "Login successful",
    }


@router.post("/refresh", response_model=schemas.AuthSessionResponse)
@limiter.limit("20/minute")
def refresh_token(
    request: Request,
    response: Response,
    payload: schemas.TokenRefreshRequest,
    db: Session = Depends(get_db)
):
    provided_refresh = payload.refresh_token or request.cookies.get("refresh_token")
    if not provided_refresh:
        # Keep validation semantics stable for clients/tests that expect a 422
        # when refresh token input is absent.
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Missing refresh token")

    using_cookie_refresh = payload.refresh_token is None and request.cookies.get("refresh_token") is not None
    if using_cookie_refresh:
        csrf_cookie = request.cookies.get("csrf_token")
        csrf_header = request.headers.get("X-CSRF-Token")
        if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
            log_audit_event(
                db,
                action="auth.refresh_csrf_failed",
                ip_address=_client_ip(request),
                user_agent=_user_agent(request),
            )
            raise exceptions.AuthenticationError("CSRF validation failed")

    try:
        user_id = decode_token_sub(provided_refresh, expected_type="refresh")
        user = crud.get_user(db, user_id)

        if not user:
            raise exceptions.AuthenticationError("Token invalid or expired")

        stored_hash = _as_str(getattr(user, "refresh_token", ""))
        if stored_hash != hash_token(provided_refresh):
            security_logger.error(f"Potential token reuse/theft detected for user {user_id}")
            log_audit_event(
                db,
                action="auth.refresh_reuse_detected",
                actor_user_id=user_id,
                target_type="user",
                target_id=user_id,
                ip_address=_client_ip(request),
                user_agent=_user_agent(request),
            )
            raise exceptions.AuthenticationError("Token invalid or expired")

        new_access = create_access_token({"sub": str(user_id)})
        new_refresh = create_refresh_token({"sub": str(user_id)})
        csrf_token = secrets.token_urlsafe(32)
        crud.update_user(db, user_id, {"refresh_token": hash_token(new_refresh)})
        _set_auth_cookies(response, new_access, new_refresh, csrf_token)
        log_audit_event(
            db,
            action="auth.refresh_success",
            actor_user_id=user_id,
            target_type="user",
            target_id=user_id,
            ip_address=_client_ip(request),
            user_agent=_user_agent(request),
        )

        return {
            "token_type": "bearer",
            "user": user,
            "message": "Session refreshed",
        }
    except JWTError:
        log_audit_event(
            db,
            action="auth.refresh_invalid_jwt",
            ip_address=_client_ip(request),
            user_agent=_user_agent(request),
        )
        raise exceptions.AuthenticationError("Invalid refresh token")
    except exceptions.AuthenticationError:
        log_audit_event(
            db,
            action="auth.refresh_failed",
            ip_address=_client_ip(request),
            user_agent=_user_agent(request),
        )
        raise exceptions.AuthenticationError("Invalid refresh token")


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=schemas.RegisterResponse)
@limiter.limit("3/minute")
def register(request: Request, response: Response, user: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = crud.get_user_by_email(db, user.email)
    if existing:
        log_audit_event(
            db,
            action="auth.register_duplicate_email",
            target_type="user_email",
            ip_address=_client_ip(request),
            user_agent=_user_agent(request),
            metadata={"email": user.email},
        )
        raise exceptions.ValidationError("Email already registered")

    db_user = crud.create_user(db, user)
    user_id = _as_int(getattr(db_user, "id", 0))
    verification_token = secrets.token_urlsafe(32)

    crud.update_user(
        db,
        user_id,
        {
            "is_verified": False,
            "verification_token": verification_token,
            "refresh_token": None,
        },
    )
    db.refresh(db_user)

    auth_logger.info(f"New user registered: {user.email} (verification required)")
    log_audit_event(
        db,
        action="auth.register_success",
        actor_user_id=user_id,
        target_type="user",
        target_id=user_id,
        ip_address=_client_ip(request),
        user_agent=_user_agent(request),
    )

    env_value = (settings.ENV or "").lower()
    is_production = env_value in {"production", "prod"}

    return {
        "message": "Registration successful. Please verify your email before logging in.",
        "user": db_user,
        "requires_verification": True,
        "verification_token_preview": None if is_production else verification_token,
    }


@router.get("/verify-email")
def verify_email(token: str, db: Session = Depends(get_db)):
    user = db.query(crud.models.User).filter(crud.models.User.verification_token == token).first()
    if not user:
        raise exceptions.AuthenticationError("Invalid or expired verification token")

    user_id = _as_int(getattr(user, "id", 0))
    crud.update_user(db, user_id, {"is_verified": True, "verification_token": None})
    return {"message": "Email verified successfully"}


@router.post("/logout")
@limiter.limit("30/minute")
def logout(request: Request, response: Response, db: Session = Depends(get_db), current_user: crud.models.User = Depends(get_current_user)):
    user_id = _as_int(getattr(current_user, "id", 0))
    crud.update_user(db, user_id, {"refresh_token": None})
    _clear_auth_cookies(response)
    auth_logger.info(f"User logged out: {_as_str(getattr(current_user, 'email', ''))}")
    log_audit_event(
        db,
        action="auth.logout",
        actor_user_id=user_id,
        target_type="user",
        target_id=user_id,
        ip_address=_client_ip(request),
        user_agent=_user_agent(request),
    )
    return {"message": "Successfully logged out"}


@router.post("/request-password-reset")
@limiter.limit("10/minute")
def request_password_reset(request: Request, data: schemas.PasswordResetRequest, db: Session = Depends(get_db)):
    user = crud.get_user_by_email(db, data.email)
    if user:
        reset_token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=1)
        user_id = _as_int(getattr(user, "id", 0))
        hashed_reset = hash_token(reset_token)
        crud.update_user(db, user_id, {
            "reset_password_token": hashed_reset,
            "reset_password_expires_at": expires_at,
        })
        if _should_send_password_reset_email():
            try:
                reset_link = _build_password_reset_link(reset_token)
                send_password_reset_email(
                    to_email=_as_str(getattr(user, "email", ""), default=data.email),
                    reset_link=reset_link,
                    expires_minutes=60,
                )
            except Exception as exc:
                # Do not leak delivery internals to clients; keep generic response.
                auth_logger.warning(f"Password reset email delivery failed for user {user_id}: {exc}")
        auth_logger.info(f"Password reset requested for {data.email}.")
        log_audit_event(
            db,
            action="auth.password_reset_requested",
            actor_user_id=user_id,
            target_type="user",
            target_id=user_id,
            ip_address=_client_ip(request),
            user_agent=_user_agent(request),
        )

    return {"message": "If that email exists, a reset link has been sent."}


@router.post("/reset-password")
@limiter.limit("10/minute")
def reset_password(request: Request, data: schemas.PasswordResetConfirm, db: Session = Depends(get_db)):
    token_hash = hash_token(data.token)
    user = db.query(crud.models.User).filter(
        # Security: compare only hashed token; never accept stored hash as input token.
        crud.models.User.reset_password_token == token_hash,
        crud.models.User.reset_password_expires_at > datetime.utcnow()
    ).first()

    if not user:
        log_audit_event(
            db,
            action="auth.password_reset_failed",
            ip_address=_client_ip(request),
            user_agent=_user_agent(request),
        )
        raise exceptions.ValidationError("Invalid or expired reset token")

    from ..crud import pwd_context

    user_id = _as_int(getattr(user, "id", 0))
    crud.update_user(db, user_id, {
        "password": pwd_context.hash(data.new_password),
        "reset_password_token": None,
        "reset_password_expires_at": None,
    })
    auth_logger.info(f"Password reset successful for user {user_id}")
    log_audit_event(
        db,
        action="auth.password_reset_success",
        actor_user_id=user_id,
        target_type="user",
        target_id=user_id,
        ip_address=_client_ip(request),
        user_agent=_user_agent(request),
    )
    return {"message": "Password reset successful"}
