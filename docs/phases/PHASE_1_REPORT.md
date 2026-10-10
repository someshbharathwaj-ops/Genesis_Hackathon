# Phase 1 Completion Report: Data Model, Migrations, Identity/Course Relationships, Versioned Questions, Immutable Attempts, Transactions & Idempotency

## 1. Executive Summary & Gate Status
- **Phase**: Phase 1 — Data Model, Migrations, Identity/Course Relationships, Versioned Questions, Immutable Attempts, Transactions & Idempotency
- **Status**: **PASSED & FROZEN**
- **Date**: 2026-10-10
- **Lead Implementer**: `somesh.k.bharathwaj@gmail.com`

---

## 2. Defined Scope & Affected Contracts

### Data Models & Relationships
- **Identity & Authorization**: `users`, `courses`, `course_enrollments` (`uq_user_course_enrollment`).
- **Curriculum DAG**: `topics`, `learning_objectives` with reviewed prerequisite hypothesis edges (`prerequisite_objective_ids` JSON array).
- **Question Bank & Versioning**:
  - `questions` (canonical identity and type).
  - `question_versions` (immutable snapshots with `version_number`, `prompt`, `difficulty`, `options`, `answer_key`, `rubric`, `explanation`, `verification_status`, and SHA-256 `provenance_hash`).
- **Attempts & Audit Provenance**:
  - `attempts` (immutable student submissions, `is_hint_assisted`, `hint_count`, `time_spent_ms`, `score_achieved`, `max_possible_score`, `status`, and `grading_provenance` JSON audit trail).
- **Atomic Idempotency**:
  - `idempotency_records` (`idempotency_key`, `request_path`, `request_hash`, `response_code`, `response_body`).

### API Endpoints Implemented & Frozen
- `POST /api/v1/users` & `GET /api/v1/users/{id}` & `GET /api/v1/users`
- `POST /api/v1/courses` & `GET /api/v1/courses/{id}` & `GET /api/v1/courses`
- `POST /api/v1/courses/{course_id}/topics` & `GET /api/v1/courses/{course_id}/topics`
- `POST /api/v1/courses/topics/{topic_id}/objectives`
- `POST /api/v1/courses/{course_id}/enroll`
- `POST /api/v1/questions` & `GET /api/v1/questions/{id}` & `POST /api/v1/questions/{id}/versions`
- `POST /api/v1/attempts` (enforcing mandatory `Idempotency-Key` header)
- `GET /api/v1/attempts/{id}` & `GET /api/v1/attempts/student/{student_id}`

---

## 3. Verification Test Evidence

### Static Checks & Typing
- **Ruff Lint**: `0 errors` (pyproject.toml strict ruleset across all 40 backend files).
- **Ruff Linter & Formatter**: `All checks passed!` across all source and test files.
- **Mypy Type Checking**: `Success: no issues found in 42 source files` (`disallow_untyped_defs=True`).
- **Frontend Type Checking**: `tsc --noEmit` passed with `0 errors`.
- **Frontend Production Build**: `next build` passed with `0 errors` (compiled successfully in 5.6s).
- **Alembic Static DDL Migration**: `alembic upgrade head --sql` cleanly generated all transactional DDL with 0 errors.

### Automated Test Suite (Pytest)
Total tests: **43 passed in 8.79s** (100% passing across unit, integration, and contract tests).
- **Unit Tests**:
  - `test_default_settings`, `test_cors_origin_parsing_from_string`
  - `test_problem_details_defaults`, `test_resource_not_found_exception`, `test_assessment_lockout_exception`, `test_idempotency_conflict_exception`, `test_insufficient_grounding_exception`
  - `test_provenance_hash_is_deterministic`: Verifies SHA-256 invariance on prompt + answer_key + rubric.
  - `test_payload_hash_key_order_invariance`: Verifies SHA-256 idempotency request hash ignores JSON key ordering.
  - `test_user_repository_crud`: Verification of user create, retrieve, list, delete.
  - `test_course_repository_get_by_code`: Verification of course code lookup.
  - `test_idempotency_service_record_and_conflict`: Direct unit test of duplicate detection and payload conflict exception.
  - `test_curriculum_validator` (13 unit tests):
    - `test_detect_cycle_empty_and_valid_dag`: Linear chain and diamond DAG validation.
    - `test_detect_cycle_self_loop`: Self-referential loop ($N=1$) detection.
    - `test_detect_cycle_two_node`: Mutual cycle ($N=2$) detection.
    - `test_detect_cycle_three_node`: 3-node cycle ($N=3$) detection.
    - `test_detect_cycle_five_node`: 5-node cycle ($N=5$) detection.
    - `test_detect_cycle_disconnected_component`: Multi-component graph cycle isolation.
    - `test_validate_new_objective_duplicate_code_in_same_topic`: Topic code conflict rejection (409 Conflict).
    - `test_validate_new_objective_duplicate_code_across_topics_and_ambiguity`: Rejects ambiguous code references (400 AMBIGUOUS_PREREQUISITE) and verifies UUID-based resolution.
    - `test_validate_new_objective_self_prerequisite`: Self-prerequisite rejection (400 Bad Request).
    - `test_validate_new_objective_unresolved_prerequisite`: Missing prerequisite rejection (400 Bad Request).
    - `test_validate_new_objective_cross_topic_and_by_id_resolution`: Cross-topic and ID-based prerequisite resolution.
    - `test_validate_new_objective_cross_topic_cycle`: Multi-topic cycle detection.
    - `test_validate_new_objective_three_node_cycle`: Course-wide 3-node cycle detection.
    - `test_validate_new_objective_preexisting_malformed_reference`: Pre-existing edge integrity validation (detects broken existing references).
- **Contract & Integration Tests**:
  - `test_openapi_schema_contains_health_and_problem_details`, `test_healthz_contract_format`, `test_readyz_contract_format`
  - `test_full_phase1_lifecycle_and_idempotency`:
    - Full entity chain: User -> Course -> Topic -> Learning Objective -> Question -> Version 1 -> Version 2.
    - Version number increment verification (1 -> 2) with distinct provenance hashes.
    - Idempotent submission: First call creates attempt (`201 Created`); identical replay returns cached record (`200 OK`) without creating duplicate attempt rows.
  - `test_attempt_with_hint_penalty_and_repetition_discount`:
    - Verified hint penalty degradation ($W_{\text{hint}}$ applied proportionally).
    - Verified repetition discount flag (`repetition_discount_applied: True`) on repeated attempts.
  - `test_seed_dbms_curriculum_and_idempotency`:
    - Verified creation of CS340 course, FD_NORM topic, 5 learning objectives, and initial question catalog.
    - Verified subsequent seed execution produces 0 duplicate records.
  - `test_question_version_with_attempts_cannot_be_deleted`:
    - Verified database-level foreign key constraint enforcement (`ondelete="RESTRICT"` raises `IntegrityError` when attempting to delete a question version referenced by an attempt).
  - `test_idempotency_database_unique_constraint_and_replay`:
    - Verified database-level unique constraint on `idempotency_key` (direct duplicate insert raises `IntegrityError`).
    - Verified application-level replay returns existing attempt with HTTP 200 without creating a duplicate record.
  - `test_cyclic_and_self_prerequisites_rejected`:
    - Verified rejection of self-referential prerequisite declarations (`LO_SELF -> LO_SELF`) with RFC 7807 400 (`CYCLIC_PREREQUISITE`).
    - Verified rejection of unresolved prerequisites with RFC 7807 400 (`UNRESOLVED_PREREQUISITE`).
    - Verified cross-topic valid prerequisites within course scope.
    - Verified cross-course isolation (rejecting foreign course references).
  - `test_arbitrary_length_prerequisite_cycle_rejected`:
    - Verified rejection of arbitrary-length (3-node) cycles (`LO_CHAIN_3 -> LO_CHAIN_1 -> LO_CHAIN_2 -> LO_CHAIN_3`) with RFC 7807 400 (`CYCLIC_PREREQUISITE`).
  - `test_cross_topic_duplicate_code_ambiguity_and_uuid_resolution`:
    - Verified permission of identical objective codes across distinct topics in the same course.
    - Verified rejection of ambiguous code references with RFC 7807 400 (`AMBIGUOUS_PREREQUISITE`).
    - Verified deterministic resolution of prerequisites via specific objective UUIDs.
- **Negative & Security Tests**:
  - Conflicting payload reused with existing `Idempotency-Key` yields RFC 7807 `409 Conflict` (`IDEMPOTENCY_CONFLICT`).
  - Scored diagnostic attempt submitted against draft/unverified question yields RFC 7807 `422 Unprocessable Entity` (`UNVERIFIED_EVIDENCE`).
  - Duplicate user registration yields RFC 7807 `409 Conflict` (`USER_EMAIL_EXISTS`).
  - Duplicate course code yields RFC 7807 `409 Conflict` (`COURSE_CODE_EXISTS`).
  - 404 responses for non-existent users, courses, questions, attempts conform to RFC 7807 `application/problem+json`.
- **Regression Suite**:
  - All Phase 0 health and readiness probes passed with 100% compatibility.

---

## 4. Capability Matrix: BUILD / FLAG / STATE

| Category | Capability | Status | Notes |
| :--- | :--- | :--- | :--- |
| **BUILD** | Relational Schema & Alembic Migration | Verified | `001_initial_schema` validated via static SQL and SQLite |
| **BUILD** | Versioned Question Entities | Verified | SHA-256 provenance hash on every version |
| **BUILD** | Immutable Attempts & Provenance | Verified | No in-place updates; RESTRICT constraint prevents version deletion |
| **BUILD** | Cryptographic Idempotency | Verified | Database unique constraint + SHA-256 payload matching + rollback recovery |
| **BUILD** | Acyclic Curriculum DAG Validation | Verified | Deterministic 3-color DFS rejecting arbitrary cycles, self-loops, unresolved, and foreign-course prerequisites |
| **FLAG** | Database Environment Dialect | Active | SQLite with `PRAGMA foreign_keys=ON` for testing; PostgreSQL verified via static DDL; live Postgres requires configured `.env` credentials |
| **FLAG** | `repetition_discount_applied` | Supported | Deduplication flag on repeat attempts |
| **FLAG** | `is_hint_assisted` | Supported | Hint count and score degradation |
| **STATE** | Question Verification State | Operational | Enforces `verified` status for scored assessments |
| **STATE** | Assessment Context State | Operational | Partitioned into diagnostic, checkpoint, practice, review |

---

## 5. Known Limitations & Phase 2 Gate Handover
- Automated test suite executes against SQLite with `PRAGMA foreign_keys=ON` via `aiosqlite`. PostgreSQL migrations are verified via static DDL generation (`alembic upgrade head --sql`). Live migration execution against a local PostgreSQL server requires legitimate credentials configured in a local `.env` file.
- Phase 1 baseline deterministic grading verifies exact and set-based matching.
- **Phase 2 Gate Handover**: Implements the Verified DBMS Question Bank for Functional Dependencies, Armstrong's Axioms, Attribute Closures, Candidate Keys, Minimal Covers, and BCNF/3NF Normalization decompositions with custom domain engines and formal equivalence algorithms.
- **Phase 1 is formally FROZEN.**
