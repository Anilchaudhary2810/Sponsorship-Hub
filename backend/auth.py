from datetime import datetime, timedelta
from typing import Optional, Any
import hmac
import hashlib

from jose import JWTError, jwt
from fastapi import Depends, Request, WebSocket
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .database import get_db
from .crud import get_user


from .config import settings
from .exceptions import AuthenticationError

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def hash_token(token: str) -> str:
    return hmac.new(
        SECRET_KEY.encode("utf-8"),
        token.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

def decode_token_sub(token: str, expected_type: str) -> int:
    payload: dict[str, Any] = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    if payload.get("type") != expected_type:
        raise AuthenticationError("Invalid token type")
    sub_val = payload.get("sub")
    if sub_val is None:
        raise AuthenticationError("Invalid token payload")
    try:
        return int(str(sub_val))
    except (TypeError, ValueError):
        raise AuthenticationError("Invalid token subject")


def get_ws_access_token(websocket: WebSocket) -> Optional[str]:
    cookie_token = websocket.cookies.get("access_token")
    if cookie_token:
        return cookie_token

    # Fallback for non-cookie clients: pass token via websocket subprotocol.
    # Supported forms:
    # 1) ["access_token", "<jwt>"] or ["bearer", "<jwt>"]
    # 2) ["access_token.<jwt>"] or ["bearer.<jwt>"]
    protocol_header = websocket.headers.get("sec-websocket-protocol", "")
    offered = [segment.strip() for segment in protocol_header.split(",") if segment.strip()]
    if not offered:
        return None

    if len(offered) >= 2 and offered[0] in {"access_token", "bearer"}:
        return offered[1]

    for protocol in offered:
        if protocol.startswith("access_token."):
            token = protocol[len("access_token.") :]
            if token:
                return token
        if protocol.startswith("bearer."):
            token = protocol[len("bearer.") :]
            if token:
                return token

    return None

def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    from .logger import auth_logger

    cookie_token = request.cookies.get("access_token")
    resolved_token = token or cookie_token
    if not resolved_token:
        auth_logger.error("Token rejection: Missing access token")
        raise AuthenticationError()

    using_cookie_auth = token is None and cookie_token is not None
    unsafe_methods = {"POST", "PUT", "PATCH", "DELETE"}
    if using_cookie_auth and request.method.upper() in unsafe_methods:
        csrf_cookie = request.cookies.get("csrf_token")
        csrf_header = request.headers.get("X-CSRF-Token")
        if not csrf_cookie or not csrf_header or not hmac.compare_digest(csrf_cookie, csrf_header):
            auth_logger.error("Token rejection: CSRF validation failed")
            raise AuthenticationError("CSRF validation failed")

    try:
        user_id_val = decode_token_sub(resolved_token, expected_type="access")
    except JWTError as e:
        auth_logger.error(f"Token rejection: JWT decode error: {str(e)}")
        raise AuthenticationError()
    except AuthenticationError:
        auth_logger.error("Token rejection: Invalid access token payload")
        raise

    user = get_user(db, int(user_id_val))
    if user is None:
        auth_logger.error(f"Auth Rejection: User ID {user_id_val} not found in database. The database may have been reset.")
        raise AuthenticationError(f"User account (ID: {user_id_val}) no longer exists. Please re-register or log in again.")
        
    return user

