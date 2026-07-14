"""Structured logging configuration using the Python standard library."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime


class JsonFormatter(logging.Formatter):
    """Format application log records as one JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        """Serialize a log record with stable operational fields."""
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info is not None:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: int = logging.INFO) -> None:
    """Configure the EvidenceGraph logger without replacing host log handlers."""
    application_logger = logging.getLogger("evidencegraph")
    application_logger.setLevel(level)
    application_logger.propagate = False

    if application_logger.handlers:
        return

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    application_logger.addHandler(handler)
