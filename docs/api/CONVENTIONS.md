# Recall API Conventions & Specification

## 1. Base URL & Versioning
All Recall API endpoints are versioned under the `/api/v1` prefix.
- Example: `GET https://recall.institution.edu/api/v1/healthz`
- Example: `POST https://recall.institution.edu/api/v1/attempts`

Future breaking changes will be isolated under `/api/v2` without modifying frozen `/api/v1` contracts.

---

## 2. Standard Response Envelope & HTTP Status Codes

### Successful Responses
JSON payloads return appropriate semantic status codes:
- `200 OK`: Successful synchronous retrieval or state query.
- `201 Created`: Successful entity creation (e.g., question created, attempt recorded).
- `204 No Content`: Successful execution with empty body.

### Error Responses (RFC 7807 Problem Details)
All error responses adhere to the RFC 7807 Problem Details standard:

```json
{
  "type": "https://recall.institution.edu/errors/RESOURCE_NOT_FOUND",
  "title": "Resource Not Found",
  "status": 404,
  "detail": "Question with ID 'q-dbms-fd-001' does not exist.",
  "instance": "/api/v1/questions/q-dbms-fd-001",
  "code": "RESOURCE_NOT_FOUND",
  "timestamp": "2026-10-10T17:30:00Z"
}
```

Standard Error Codes:
- `VALIDATION_ERROR` (422): Payload schema validation failed.
- `UNAUTHORIZED` (401): Missing or invalid credentials.
- `FORBIDDEN` (403): User lacks permission or attempt state is locked.
- `ASSESSMENT_LOCKOUT` (403): Free-form AI tutor query rejected during active scored assessment.
- `RESOURCE_NOT_FOUND` (404): Entity does not exist.
- `CONFLICT` (409): State conflict or version collision.
- `IDEMPOTENCY_CONFLICT` (409): Duplicate submission with conflicting payload.
- `LLM_TIMEOUT` (504): LLM inference timed out beyond strict bound; deterministic fallback applied.
- `UNVERIFIED_EVIDENCE` (422): Requested operation requires verified curriculum grounding that is absent.

---

## 3. Mandatory Headers

- `Content-Type: application/json` (unless uploading multipart documents)
- `Authorization: Bearer <token>` (for authenticated student/instructor routes)
- `Idempotency-Key: <UUID>`: **Mandatory** on state-mutating assessment endpoints (`POST /api/v1/attempts`).
  - If a request with the same `Idempotency-Key` and matching payload is retransmitted, the server returns the cached `200 OK` or `201 Created` outcome without re-evaluating or duplicating student mastery records.
  - If the key is reused with a different payload, the server returns `409 Conflict`.

---

## 4. Pagination & Filtering
List endpoints use zero-based cursor or limit/offset pagination:
- `limit` (default: 20, max: 100)
- `offset` (default: 0)

Response envelope for paginated collections:
```json
{
  "items": [...],
  "total": 42,
  "limit": 20,
  "offset": 0,
  "has_more": true
}
```

---

## 5. Standard Health & Probes
- `GET /api/v1/healthz`: Liveness check (verifies HTTP server is responding).
- `GET /api/v1/readyz`: Readiness check (verifies database connectivity and essential engine subsystems).
