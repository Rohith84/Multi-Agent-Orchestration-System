"""
Pydantic schemas for Auth Tokens, Users, Organizations, Teams, API Keys, Audit Logs, and Security Events.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class TokenSchema(BaseModel):
    """Schema for OAuth2 JWT Access Token."""

    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int = 3600
    user_id: str
    email: str
    role: str
    org_id: str


class UserLoginRequest(BaseModel):
    """Payload for user password login."""

    username: EmailStr = Field(..., description="User account email address.")
    password: str = Field(..., description="Account password.")


class UserSchema(BaseModel):
    """Schema for user profile data."""

    id: str
    org_id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrganizationSchema(BaseModel):
    """Schema for multi-tenant organization."""

    id: str
    name: str
    slug: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TeamSchema(BaseModel):
    """Schema for organization sub-team."""

    id: str
    org_id: str
    name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RoleSchema(BaseModel):
    """Schema for RBAC role and permissions."""

    id: str
    name: str
    permissions: list[str]

    model_config = ConfigDict(from_attributes=True)


class APIKeySchema(BaseModel):
    """Schema for API Key metadata."""

    id: str
    org_id: str
    user_id: str
    prefix: str
    name: str
    is_active: bool
    usage_count: int
    monthly_quota: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CreateAPIKeyRequest(BaseModel):
    """Request payload to create a new API Key."""

    name: str = Field(..., description="Descriptive name for the API Key.")
    monthly_quota: int = Field(default=100000, description="Monthly request quota.")


class APIKeyCreatedResponse(BaseModel):
    """Response containing the plaintext secret API key (shown only once)."""

    api_key: str
    key_info: APIKeySchema


class AuditLogSchema(BaseModel):
    """Schema for security and governance audit logs."""

    id: str
    org_id: str
    user_id: str | None = None
    action: str
    resource_type: str
    resource_id: str
    ip_address: str
    details: dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
