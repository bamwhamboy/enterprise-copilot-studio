"""Shared schema base classes."""

from pydantic import BaseModel, ConfigDict


class ORMBaseModel(BaseModel):
    """Base for response schemas built from SQLAlchemy ORM objects."""

    model_config = ConfigDict(from_attributes=True)
