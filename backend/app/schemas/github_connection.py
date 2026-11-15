"""API schemas for GitHub repository connections."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class GitHubConnectionCreate(BaseModel):
    repository_owner: str = Field(min_length=1, max_length=255)
    repository_name: str = Field(min_length=1, max_length=255)
    token: str = Field(min_length=1)


class GitHubConnectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    knowledge_source_id: uuid.UUID
    repository_owner: str
    repository_name: str
    sync_status: str
    last_synced_at: datetime | None
    created_at: datetime
    updated_at: datetime
