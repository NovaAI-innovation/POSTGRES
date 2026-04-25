from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _b64url_decode(raw: str) -> bytes:
    padding = "=" * ((4 - len(raw) % 4) % 4)
    return base64.urlsafe_b64decode(raw + padding)


@dataclass(frozen=True)
class TokenValidationResult:
    ok: bool
    payload: dict[str, Any] | None = None
    error: str | None = None


def issue_signed_token(claims: dict[str, Any], secret: str, expires_in_seconds: int = 3600) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    body = dict(claims)
    body["exp"] = int(time.time()) + expires_in_seconds
    header_segment = _b64url_encode(json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    payload_segment = _b64url_encode(json.dumps(body, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    signing_input = f"{header_segment}.{payload_segment}".encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{header_segment}.{payload_segment}.{_b64url_encode(signature)}"


def validate_signed_token(token: str, secrets: list[str]) -> TokenValidationResult:
    parts = token.split(".")
    if len(parts) != 3:
        return TokenValidationResult(ok=False, error="invalid_format")
    header_segment, payload_segment, sig_segment = parts
    signing_input = f"{header_segment}.{payload_segment}".encode("utf-8")
    try:
        sent_sig = _b64url_decode(sig_segment)
    except Exception:
        return TokenValidationResult(ok=False, error="invalid_signature")

    valid_signature = False
    for secret in secrets:
        expected = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
        if hmac.compare_digest(expected, sent_sig):
            valid_signature = True
            break
    if not valid_signature:
        return TokenValidationResult(ok=False, error="invalid_signature")

    try:
        payload = json.loads(_b64url_decode(payload_segment).decode("utf-8"))
    except Exception:
        return TokenValidationResult(ok=False, error="invalid_payload")

    exp = payload.get("exp")
    if not isinstance(exp, int):
        return TokenValidationResult(ok=False, error="missing_exp")
    if int(time.time()) >= exp:
        return TokenValidationResult(ok=False, error="expired_token")
    return TokenValidationResult(ok=True, payload=payload)
