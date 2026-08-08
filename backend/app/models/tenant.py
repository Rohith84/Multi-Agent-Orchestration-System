"""
Organization, Team, User, Role, APIKey, and AuditLog SQLAlchemy models.

Provides multi-tenant data isolation, role-based access control (RBAC), API key management with usage quotas, and security audit logs.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, Uuid, func, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Organization(Base):
    """
    Multi-tenant organization boundary.
    """

    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    slug: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Organization(id={self.id}, name='{self.name}', slug='{self.slug}')>"


class Team(Base):
    """
    Sub-team within an organization.
    """

    __tablename__ = "teams"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Team(id={self.id}, name='{self.name}', org_id={self.org_id})>"


class User(Base):
    """
    Authenticated user account with RBAC role.
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="",
    )
    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="Developer",
    )  # Platform Admin, Org Admin, Architect, Developer, Reviewer, Auditor, Viewer
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    organization = relationship("Organization", back_populates="users")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', role='{self.role}')>"


class Role(Base):
    """
    RBAC Role and permission mapping.
    """

    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
    )
    permissions: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    def __repr__(self) -> str:
        return f"<Role(name='{self.name}', perms_count={len(self.permissions)})>"


class APIKey(Base):
    """
    Hashed API Key for external program API access with token quotas.
    """

    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    key_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )
    prefix: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    usage_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    monthly_quota: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=100000,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<APIKey(name='{self.name}', prefix='{self.prefix}', usage={self.usage_count})>"


class AuditLog(Base):
    """
    Security and governance audit log event.
    """

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        nullable=True,
    )
    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    resource_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    resource_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="",
    )
    ip_address: Mapped[str] = mapped_column(
        String(45),
        nullable=False,
        default="127.0.0.1",
    )
    details: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<AuditLog(action='{self.action}', resource='{self.resource_type}')>"
