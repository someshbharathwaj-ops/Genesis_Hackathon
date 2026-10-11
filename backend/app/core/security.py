"""Cryptographic token generation and verification using HMAC-SHA256.

Adheres to standard JWT format without external binary dependencies.
Token envelope: base64url(header).base64url(payload).base64url(signature)
"""

import base64
import hashlib
import hmac
import json
import time
from typing import Any

from app.core.config import settings
from app.core.errors import RecallException


def _b64url_encode(data: bytes) -> str:
    """Encode bytes to URL-safe base64 without padding."""
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64url_decode(s: str) -> bytes:
    """Decode URL-safe base64 with auto-padding."""
    padding = 4 - (len(s) % 4)
    if padding and padding < 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s.encode("utf-8"))


def create_access_token(
    user_id: str,
    email: str,
    role: str,
    expires_minutes: int | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Create a signed JWT access token.

    Args:
        user_id: Subject user ID.
        email: User email address.
        role: User role (student, instructor, admin).
        expires_minutes: Validity duration in minutes.
        extra_claims: Optional extra key-value pairs.

    Returns:
        Compact signed JWT string.
    """
    now = int(time.time())
    ttl_seconds = (expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES) * 60
    exp = now + ttl_seconds

    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "iat": now,
        "exp": exp,
    }
    if extra_claims:
        payload.update(extra_claims)

    header_bytes = json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")

    header_b64 = _b64url_encode(header_bytes)
    payload_b64 = _b64url_encode(payload_bytes)

    signing_input = f"{header_b64}.{payload_b64}".encode()
    signature = hmac.new(
        settings.SECRET_KEY.encode(),
        signing_input,
        hashlib.sha256,
    ).digest()
    sig_b64 = _b64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_access_token(token: str) -> dict[str, Any]:
    """Verify and decode a signed JWT access token.

    Args:
        token: Compact JWT string.

    Returns:
        Decoded payload dictionary.

    Raises:
        RecallException: If signature is invalid, token is expired, or structure is malformed.
    """
    parts = token.strip().split(".")
    if len(parts) != 3:
        raise RecallException(
            status_code=401,
            code="UNAUTHORIZED",
            title="Invalid Token",
            detail="Token structure is malformed.",
        )

    header_b64, payload_b64, sig_b64 = parts

    signing_input = f"{header_b64}.{payload_b64}".encode()
    expected_sig = hmac.new(
        settings.SECRET_KEY.encode(),
        signing_input,
        hashlib.sha256,
    ).digest()
    expected_sig_b64 = _b64url_encode(expected_sig)

    # Constant-time comparison
    if not hmac.compare_digest(sig_b64, expected_sig_b64):
        raise RecallException(
            status_code=401,
            code="UNAUTHORIZED",
            title="Invalid Token",
            detail="Token signature verification failed.",
        )

    try:
        payload_bytes = _b64url_decode(payload_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception as exc:
        raise RecallException(
            status_code=401,
            code="UNAUTHORIZED",
            title="Invalid Token",
            detail=f"Failed to decode token payload: {exc}",
        ) from exc

    exp = payload.get("exp")
    if exp is not None and int(exp) < int(time.time()):
        raise RecallException(
            status_code=401,
            code="UNAUTHORIZED",
            title="Token Expired",
            detail="Authentication token has expired. Please log in again.",
        )

    return payload
