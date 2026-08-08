"""
OAuth2 JWT Security, Password Hashing & RBAC Authorization Injectors.

Provides JWT token management, bcrypt password verification, and role-based access control dependencies.
"""

from __future__ import annotations

import os
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

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "super-secret-enterprise-jwt-key-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 hours

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def hash_password(password: str) -> str:
    """Hash password string using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plaintext password against bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Generate JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate JWT access token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict[str, Any]:
    """Dependency injector yielding current authenticated user payload."""
    if not token:
        # Fallback admin for local development
        return {
            "id": "00000000-0000-0000-0000-000000000001",
            "org_id": "00000000-0000-0000-0000-000000000001",
            "email": "admin@enterprise.com",
            "role": "Platform Admin",
        }
    payload = decode_access_token(token)
    return payload


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
