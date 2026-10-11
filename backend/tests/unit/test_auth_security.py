"""Unit tests for cryptographic token signing, expiration, and tampering detection."""

import time

import pytest

from app.core.errors import RecallException
from app.core.security import create_access_token, decode_access_token


@pytest.mark.unit
def test_create_and_decode_valid_token() -> None:
    """Ensure standard access token is generated and decoded accurately."""
    token = create_access_token(
        user_id="user-123",
        email="test@recall.edu",
        role="student",
        expires_minutes=60,
        extra_claims={"tenant": "demo"},
    )
    assert token.count(".") == 2

    claims = decode_access_token(token)
    assert claims["sub"] == "user-123"
    assert claims["email"] == "test@recall.edu"
    assert claims["role"] == "student"
    assert claims["tenant"] == "demo"
    assert claims["exp"] > time.time()


@pytest.mark.unit
def test_expired_token_rejection() -> None:
    """Ensure expired token raises 401 with descriptive detail."""
    # Negative expiry
    token = create_access_token(
        user_id="user-123",
        email="test@recall.edu",
        role="student",
        expires_minutes=-5,
    )
    with pytest.raises(RecallException) as exc_info:
        decode_access_token(token)

    assert exc_info.value.status_code == 401
    assert exc_info.value.code == "UNAUTHORIZED"
    assert "expired" in exc_info.value.detail.lower()


@pytest.mark.unit
def test_tampered_token_signature_rejection() -> None:
    """Ensure tampered payload signature mismatch is rejected."""
    token = create_access_token(
        user_id="user-123",
        email="test@recall.edu",
        role="student",
    )
    header, payload, sig = token.split(".")
    # Tamper payload
    tampered_token = f"{header}.eyJyYW5kb20iOiAidGFtcGVyZWQifQ.{sig}"

    with pytest.raises(RecallException) as exc_info:
        decode_access_token(tampered_token)

    assert exc_info.value.status_code == 401
    assert exc_info.value.code == "UNAUTHORIZED"
    assert "signature" in exc_info.value.detail.lower()


@pytest.mark.unit
def test_malformed_token_rejection() -> None:
    """Ensure tokens without 3 dots are rejected immediately."""
    with pytest.raises(RecallException) as exc_info:
        decode_access_token("not-a-token")
    assert exc_info.value.status_code == 401

    with pytest.raises(RecallException) as exc_info2:
        decode_access_token("part1.part2")
    assert exc_info2.value.status_code == 401
