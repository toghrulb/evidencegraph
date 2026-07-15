"""Request and response schemas for research collections."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CollectionCreate(BaseModel):
    """Fields accepted when creating a collection."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=10_000)

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        """Normalize surrounding whitespace and reject whitespace-only names."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("Collection name cannot be blank.")
        return normalized

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        """Store an omitted description instead of an empty string."""
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class CollectionRead(BaseModel):
    """Persisted collection metadata returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime
