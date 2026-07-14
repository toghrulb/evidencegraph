"""Tests for application health semantics."""

from fastapi import status
from fastapi.testclient import TestClient

from app.main import create_app


def test_liveness_reports_ok_before_lifespan_startup() -> None:
    """Liveness remains independent from application readiness."""
    client = TestClient(create_app())

    response = client.get("/health/live")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok"}


def test_readiness_is_unavailable_before_lifespan_startup() -> None:
    """A process is not ready until its startup lifecycle completes."""
    client = TestClient(create_app())

    response = client.get("/health/ready")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json() == {"status": "not_ready"}


def test_readiness_reports_ready_during_application_lifespan() -> None:
    """A started application reports readiness."""
    application = create_app()

    with TestClient(application) as client:
        response = client.get("/health/ready")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ready"}
    assert application.state.ready is False
