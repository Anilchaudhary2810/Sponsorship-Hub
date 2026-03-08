from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
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

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

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

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    from .logger import auth_logger
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            auth_logger.error("Token rejection: Invalid token type in payload")
            raise AuthenticationError("Invalid token type")
            
        user_id_val = payload.get("sub")
        if user_id_val is None:
            auth_logger.error("Token rejection: No 'sub' field in payload")
            raise AuthenticationError()
    except JWTError as e:
        auth_logger.error(f"Token rejection: JWT decode error: {str(e)}")
        raise AuthenticationError()

    user = get_user(db, int(user_id_val))
    if user is None:
        auth_logger.error(f"Auth Rejection: User ID {user_id_val} not found in database. The database may have been reset.")
        raise AuthenticationError(f"User account (ID: {user_id_val}) no longer exists. Please re-register or log in again.")
        
    return user

