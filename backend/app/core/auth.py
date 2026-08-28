"""
OAuth2 JWT Security, Password Hashing & RBAC Authorization Injectors.

Provides JWT token management, bcrypt password verification, and role-based access control dependencies.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 hours

import bcrypt

# oauth2_scheme setup
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=True)
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def _get_secret_key() -> str:
    """Load JWT secret from settings (env-driven, not hardcoded)."""
    return get_settings().jwt_secret_key


def hash_password(password: str) -> str:
    """Hash password string using bcrypt."""
    pw_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pw_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plaintext password against bcrypt hash."""
    try:
        pw_bytes = plain_password.encode("utf-8")
        hash_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(pw_bytes, hash_bytes)
    except Exception:
        return False


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Generate JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, _get_secret_key(), algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate JWT access token."""
    try:
        payload = jwt.decode(token, _get_secret_key(), algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict[str, Any]:
    """
    Dependency injector yielding current authenticated user payload.

    Requires a valid JWT token. Returns 401 if missing or invalid.
    """
    payload = decode_access_token(token)
    if not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token: missing subject",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


async def get_optional_user(token: str | None = Depends(oauth2_scheme_optional)) -> dict[str, Any] | None:
    """
    Optional authentication dependency.

    Returns user payload if a valid token is present, None otherwise.
    Used for endpoints that can work with or without authentication.
    """
    if not token:
        return None
    try:
        payload = decode_access_token(token)
        return payload if payload.get("sub") else None
    except HTTPException:
        return None


def require_role(allowed_roles: list[str]):
    """Dependency factory enforcing RBAC role checks."""

    async def _role_checker(user: dict[str, Any] = Depends(get_current_user)):
        user_role = user.get("role", "Viewer")
        if user_role not in allowed_roles and "Platform Admin" not in user_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Action requires one of roles: {', '.join(allowed_roles)}",
            )
        return user

    return _role_checker
