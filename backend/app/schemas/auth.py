"""Schemas for authentication & authorization."""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMBaseModel


class UserRegister(BaseModel):
    """Payload for ``POST /auth/register``.

    ``organization_name`` joins an existing organization of that name
    (as an ``end_user``) if one exists, or creates a new one (the
    registering user becomes its ``organization_admin``) if not --
    see AuthService.register() for the exact rule.
    """

    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    full_name: str | None = Field(default=None, max_length=255)
    organization_name: str = Field(min_length=1, max_length=255)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # access token lifetime, in seconds


class RefreshRequest(BaseModel):
    refresh_token: str


class RoleRead(ORMBaseModel):
    id: uuid.UUID
    name: str
    description: str | None


class OrganizationRead(ORMBaseModel):
    id: uuid.UUID
    name: str
    created_at: datetime


class UserRead(ORMBaseModel):
    id: uuid.UUID
    email: str
    full_name: str | None
    is_active: bool
    organization_id: uuid.UUID
    role: RoleRead
    created_at: datetime
