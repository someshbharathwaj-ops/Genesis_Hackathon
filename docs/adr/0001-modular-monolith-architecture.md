# ADR 0001: Modular Monolith Architecture for Recall

## Status
Accepted

## Date
2026-10-10

## Context & Problem Statement
Recall requires high consistency across state-mutating operations: adaptive question sequencing, atomic attempt submissions, deterministic grading provenance, and vector retrieval. A microservices architecture introduces network latency, distributed transaction complexities (sagas/2PC), operational overhead, and potential race conditions between assessment state and tutor lockout checks.

## Decision Drivers
- High consistency and ACID transactions for question attempts and grading provenance.
- Zero distributed latency when querying student state to enforce tutor lockout.
- Simplified operational model for local deployment, CI execution, and institutional on-premise compliance.
- Strict logical boundaries separating the Adaptive Learning Engine, Knowledge Engine, and AI Execution Engine.

## Considered Alternatives
1. **Microservices (Services for Auth, ALE, Knowledge/Vector, and LLM)**:
   - Rejected due to distributed state synchronization complexity, network hops on attempt grading, and excessive deployment overhead for small-team maintenance.
2. **Modular Monolith in Python/FastAPI with PostgreSQL + pgvector**:
   - Chosen. Provides clean module isolation, shared high-speed transactions, pgvector colocation with relation tables, and zero-network overhead for engine-to-engine state inspection.

## Consequences
- **Positive**: Single codebase, shared database transaction boundary, instant consistency, atomic grading and mastery updates.
- **Negative**: Must strictly enforce internal package dependency boundaries (no circular imports between modules).
