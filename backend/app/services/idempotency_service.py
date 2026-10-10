"""Deterministic Idempotency Service preventing replay discrepancies."""

import hashlib
import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import IdempotencyConflictError
from app.models.attempt import IdempotencyRecord
from app.repositories.idempotency_repo import IdempotencyRepository


def compute_payload_hash(payload: Any) -> str:
    """Compute deterministic SHA-256 hash of structured payload."""
    if isinstance(payload, dict | list):
        canonical_str = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    elif isinstance(payload, bytes):
        return hashlib.sha256(payload).hexdigest()
    else:
        canonical_str = str(payload).strip()

    return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()


class IdempotencyService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = IdempotencyRepository(session)

    async def get_existing_result(
        self, idempotency_key: str, request_payload: Any
    ) -> tuple[int, dict[str, Any]] | None:
        """Check if request was previously processed with identical payload."""
        existing = await self.repo.get_by_key(idempotency_key)
        if not existing:
            return None

        current_hash = compute_payload_hash(request_payload)
        if existing.request_hash != current_hash:
            raise IdempotencyConflictError(idempotency_key)

        cached_data = json.loads(existing.response_body)
        return existing.response_code, cached_data

    async def record_response(
        self,
        idempotency_key: str,
        request_path: str,
        request_payload: Any,
        status_code: int,
        response_body: dict[str, Any],
    ) -> IdempotencyRecord:
        """Persist processed outcome under the given idempotency key."""
        payload_hash = compute_payload_hash(request_payload)
        record = IdempotencyRecord(
            idempotency_key=idempotency_key,
            request_path=request_path,
            request_hash=payload_hash,
            response_code=status_code,
            response_body=json.dumps(response_body),
        )
        await self.repo.create(record)
        return record
