"""Schemas returned by health endpoints."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class LivenessResponse(BaseModel):
    """Liveness probe response."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"] = "ok"


class ReadinessResponse(BaseModel):
    """Readiness probe response."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ready", "not_ready"]
