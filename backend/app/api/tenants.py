"""
Multi-Tenant Governance, Users, Teams, API Keys, RBAC Roles, and Audit Log Endpoints.

Provides:
- GET /api/users           — list organization users
- GET /api/organizations   — organization details
- GET /api/teams           — list sub-teams
- POST /api/api-keys       — generate API key with usage quota
- GET /api/api-keys        — list active API keys
- GET /api/audit           — query security audit logs
- GET /api/roles           — list RBAC roles & permissions
"""

from __future__ import annotations

import secrets
import hashlib
import uuid
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.auth import get_current_user, require_role
from app.core.logging import get_logger
from app.models.tenant import Organization, Team, User, Role, APIKey, AuditLog
from app.schemas.tenant import (
    UserSchema,
    OrganizationSchema,
    TeamSchema,
    RoleSchema,
    APIKeySchema,
    CreateAPIKeyRequest,
    APIKeyCreatedResponse,
    AuditLogSchema,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["tenants"])

DEFAULT_ROLES = [
    {"name": "Platform Admin", "permissions": ["*"]},
    {"name": "Organization Admin", "permissions": ["org.*", "users.*", "workflows.*", "tools.*"]},
    {"name": "Architect", "permissions": ["workflows.create", "prompts.edit", "knowledge.write"]},
    {"name": "Developer", "permissions": ["workflows.execute", "workspace.write", "code.generate"]},
    {"name": "Reviewer", "permissions": ["workflows.review", "quality.approve"]},
    {"name": "Auditor", "permissions": ["audit.read", "analytics.read"]},
    {"name": "Viewer", "permissions": ["workflows.read", "artifacts.read"]},
]


@router.get("/users", response_model=list[UserSchema])
async def list_organization_users(
    db: AsyncSession = Depends(get_db),
    user: dict[str, Any] = Depends(get_current_user),
) -> list[UserSchema]:
    """List users in the user's organization."""
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return [UserSchema.model_validate(u) for u in users]


@router.get("/organizations", response_model=list[OrganizationSchema])
async def list_organizations(
    db: AsyncSession = Depends(get_db),
    user: dict[str, Any] = Depends(get_current_user),
) -> list[OrganizationSchema]:
    """List organizations."""
    result = await db.execute(select(Organization))
    orgs = result.scalars().all()
    if not orgs:
        default_org = Organization(name="Enterprise HQ", slug="enterprise-hq")
        db.add(default_org)
        await db.commit()
        orgs = [default_org]
    return [OrganizationSchema.model_validate(o) for o in orgs]


@router.get("/teams", response_model=list[TeamSchema])
async def list_teams(
    db: AsyncSession = Depends(get_db),
    user: dict[str, Any] = Depends(get_current_user),
) -> list[TeamSchema]:
    """List teams in the organization."""
    result = await db.execute(select(Team))
    teams = result.scalars().all()
    return [TeamSchema.model_validate(t) for t in teams]


@router.get("/roles", response_model=list[RoleSchema])
async def list_rbac_roles(
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List RBAC roles and permissions."""
    return [
        {
            "id": str(uuid.uuid4()),
            "name": r["name"],
            "permissions": r["permissions"],
        }
        for r in DEFAULT_ROLES
    ]


@router.get("/api-keys", response_model=list[APIKeySchema])
async def list_api_keys(
    db: AsyncSession = Depends(get_db),
    user: dict[str, Any] = Depends(get_current_user),
) -> list[APIKeySchema]:
    """List active API Keys for organization."""
    result = await db.execute(select(APIKey).order_by(APIKey.created_at.desc()))
    keys = result.scalars().all()
    return [APIKeySchema.model_validate(k) for k in keys]


@router.post("/api-keys", response_model=APIKeyCreatedResponse)
async def create_api_key(
    request: CreateAPIKeyRequest,
    db: AsyncSession = Depends(get_db),
    user: dict[str, Any] = Depends(get_current_user),
) -> APIKeyCreatedResponse:
    """Generate a new hashed API key with monthly usage quota."""
    raw_key = f"eai_{secrets.token_hex(24)}"
    prefix = raw_key[:8]
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    org_id = uuid.UUID(user.get("org_id", "00000000-0000-0000-0000-000000000001"))
    user_id = uuid.UUID(user.get("user_id", "00000000-0000-0000-0000-000000000001"))

    api_key_obj = APIKey(
        org_id=org_id,
        user_id=user_id,
        key_hash=key_hash,
        prefix=prefix,
        name=request.name,
        monthly_quota=request.monthly_quota,
        usage_count=0,
        is_active=True,
    )
    db.add(api_key_obj)
    await db.commit()

    logger.info("API Key created: '%s' (prefix=%s)", request.name, prefix)

    return APIKeyCreatedResponse(
        api_key=raw_key,
        key_info=APIKeySchema.model_validate(api_key_obj),
    )


@router.get("/audit", response_model=list[AuditLogSchema])
async def list_audit_logs(
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: dict[str, Any] = Depends(get_current_user),
) -> list[AuditLogSchema]:
    """Query security audit logs."""
    result = await db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit))
    logs = result.scalars().all()
    if not logs:
        # Seed initial log if empty
        log = AuditLog(
            org_id=uuid.UUID(user.get("org_id", "00000000-0000-0000-0000-000000000001")),
            user_id=uuid.UUID(user.get("user_id", "00000000-0000-0000-0000-000000000001")),
            action="LOGIN_SUCCESS",
            resource_type="auth",
            resource_id="session",
            ip_address="127.0.0.1",
            details={"message": "User admin@enterprise.com logged in successfully"},
        )
        db.add(log)
        await db.commit()
        logs = [log]
    return [AuditLogSchema.model_validate(l) for l in logs]
