from __future__ import annotations

import json
import logging
from typing import Any


SENSITIVE_KEYS = {"authorization", "x-api-key", "token", "secret", "password"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        extra = getattr(record, "extra_payload", None)
        if isinstance(extra, dict):
            payload["context"] = _scrub(extra)
        return json.dumps(payload, ensure_ascii=True)


def _scrub(data: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key, value in data.items():
        if key.lower() in SENSITIVE_KEYS:
            cleaned[key] = "***"
        else:
            cleaned[key] = value
    return cleaned


def configure_logging(level: str) -> None:
    root = logging.getLogger()
    root.setLevel(level.upper())
    if root.handlers:
        for handler in root.handlers:
            handler.setFormatter(JsonFormatter())
        return
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
