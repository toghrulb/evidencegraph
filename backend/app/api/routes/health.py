"""Application health endpoints."""

from fastapi import APIRouter, Request, Response, status

from app.schemas.health import LivenessResponse, ReadinessResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get(
    "/live",
    response_model=LivenessResponse,
    summary="Check process liveness",
)
async def liveness() -> LivenessResponse:
    """Report that the API process can serve requests."""
    return LivenessResponse()


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "Application startup has not completed or shutdown has begun.",
            "model": ReadinessResponse,
        }
    },
    summary="Check application readiness",
)
async def readiness(request: Request, response: Response) -> ReadinessResponse:
    """Report whether application lifecycle startup has completed."""
    if not bool(getattr(request.app.state, "ready", False)):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadinessResponse(status="not_ready")

    return ReadinessResponse(status="ready")
