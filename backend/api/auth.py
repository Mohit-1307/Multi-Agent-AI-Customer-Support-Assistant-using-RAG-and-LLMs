"""
TechMart AI Support — Authentication (JWT + bcrypt)

Handles password hashing/verification and JWT access-token creation
and validation, plus FastAPI dependency functions used to protect
routes that require a logged-in (or admin) user.
"""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from ..config import settings
from ..database.db import get_db
from ..database.db import User

# bcrypt-based password hashing context — "deprecated=auto" upgrades old
# hashes automatically if the hashing scheme ever changes in the future
pwd_context = CryptContext(schemes = ["bcrypt"], deprecated = "auto")

# Reads the "Authorization: Bearer <token>" header from incoming requests
bearer_scheme = HTTPBearer()


# ------------------------------------------------------------------
# Password helpers
# ------------------------------------------------------------------
def hash_password(password: str) -> str:
    
    "Hash a plain-text password before storing it in the database."

    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    
    "Check a plain-text password against a stored bcrypt hash."

    return pwd_context.verify(plain, hashed)


# ------------------------------------------------------------------
# JWT helpers
# ------------------------------------------------------------------
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    
    "Create a signed JWT access token containing the given payload plus an expiry timestamp."

    payload = data.copy()

    expire = datetime.utcnow() + (expires_delta or timedelta(minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES))

    payload.update({"exp": expire})

    return jwt.encode(payload, settings.SECRET_KEY, algorithm = settings.ALGORITHM)


def decode_token(token: str) -> dict:
    
    "Decode and verify a JWT token, raising a 401 error if it's invalid, tampered with, or expired."

    try:

        return jwt.decode(token, settings.SECRET_KEY, algorithms = [settings.ALGORITHM])

    except JWTError:

        raise HTTPException(

            status_code = status.HTTP_401_UNAUTHORIZED,

            detail = "Invalid or expired token",

            headers = {"WWW-Authenticate": "Bearer"}

        )


# -----------------------------------------------------------------------
# FastAPI Dependencies — used with Depends(...) in route definitions
# -----------------------------------------------------------------------
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme), db: Session = Depends(get_db)) -> User:
    
    "Dependency that extracts and validates the current user from the request's bearer token. Raises 401 if the token or user is invalid. Add this as a route parameter to require login for that endpoint."

    payload = decode_token(credentials.credentials)

    user_id: str = payload.get("sub")

    if not user_id:

        raise HTTPException(status_code = 401, detail = "Invalid token payload")

    user = db.query(User).filter(User.id == user_id).first()

    if not user:

        raise HTTPException(status_code = 401, detail = "User not found")

    return user


def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    
    """
    Dependency that additionally requires the current user to be an admin.
    Builds on get_current_user, so it also enforces basic login first.
    """

    if not current_user.is_admin:

        raise HTTPException(status_code = 403, detail = "Admin access required")

    return current_user


# --------------------------------------------------------------------------
# Optional Auth — returns None instead of raising if no token is provided
# --------------------------------------------------------------------------
def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error = False)), db: Session = Depends(get_db)) -> Optional[User]:
    
    "Like get_current_user, but for endpoints that work whether or not the caller is logged in — returns None instead of raising an error if no valid token is present."

    if not credentials:

        return None

    try:

        payload = decode_token(credentials.credentials)

        user_id = payload.get("sub")

        return db.query(User).filter(User.id == user_id).first()

    except HTTPException:

        # Any decode/lookup failure just means "not logged in" here, not an error
        return None
