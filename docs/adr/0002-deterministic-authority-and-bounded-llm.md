# ADR 0002: Deterministic Business Authority and Bounded LLM Role

## Status
Accepted

## Date
2026-10-10

## Context & Problem Statement
Educational AI systems frequently suffer from non-deterministic grading, hallucinated curriculum facts, sycophancy (agreeing with student errors), and unearned mastery updates. We must establish an unbreachable boundary between deterministic domain logic and stochastic language models.

## Decision Drivers
- Grading must be reproducible, auditable, and immutable.
- Mastery scores and confidence estimates must follow mathematical formulas, not LLM opinions.
- Active scored assessments must strictly lock out AI tutor explanations to prevent unauthorized assistance.
- Grounded revision must cite authentic ingested curriculum materials or explicitly abstain.

## Decision
1. **Authoritative Code**:
   - Deterministic Python algorithms compute all grades, objective coverage, evidence confidence, attempt eligibility, diagnostic routing, and spaced repetition schedules.
   - Database transactions commit immutable grading records with complete provenance.
2. **Bounded Model Execution & Collaborative SLM Verification**:
   - The language model layer is restricted to text summarization, grounded Socratic hinting (only when permitted by policy), and structured explanation formatting.
   - For generative explanation and review tasks, the target design utilizes a collaborative Small Language Model (SLM) verification pipeline with role-differentiated generation, evidence review, and adversarial challenge (Generator, Evidence Reviewer, Challenger) coordinated by a deterministic Verification Controller.
   - Output from models is validated against strict Pydantic schemas.
   - Under no circumstances does model output modify student mastery state, assign grades, or override grading keys.
   - For formal technical domains (such as Relational DBMS logic), deterministic backend algorithms and known-answer test suites are used directly rather than delegating correctness to language models.

## Consequences
- **Positive**: Complete auditability, academic integrity, zero risk of grading drift or hallucinated mastery credentials.
- **Negative**: Requires rigorous manual and programmatic specification of rubrics, schemas, and question bank test cases.
