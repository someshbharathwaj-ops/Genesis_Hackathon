# Recall — Phase 3 Report: Evidence and Bounded Diagnosis

**Phase**: 3 (Evidence Representation and Bounded Diagnosis)  
**Branch**: `feature/phase-3-evidence-diagnosis` (derived from `e4a88ed`, tagged `phase-2-frozen`)  
**Base Commit / Frozen Tags**: `phase-0-frozen` (`fa1c70e`), `phase-1-frozen` (`16895b7`), `phase-2-frozen` (`e4a88ed`)  
**Evaluation Date**: 2026-10-11  
**Status**: COMPLETE (Gated Verification Succeeded)

---

## 1. Executive Summary

Phase 3 implements **Evidence Representation and Bounded Diagnosis**, allowing Recall to reliably represent student learning evidence from immutable attempt ledgers, decouple performance from confidence, detect evidence conflicts, identify error signatures without jumping to ungrounded conclusions, attribute prerequisite gaps across curriculum DAGs, and plan bounded diagnostic sessions.

All 74 tests in the comprehensive test suite (contract, integration, regression, and unit) pass cleanly with zero failures. Static type checking (`mypy`), linting (`ruff`), database static DDL generation (`alembic`), and frontend production compilation (`tsc`, `next build`) succeed with zero errors.

---

## 2. Architecture & Design Implementation

### A. Evidence Representation & Audited Ledger (`app/modules/adaptive_learning/diagnosis_engine.py`)
Extracts and categorizes evidence units from immutable attempt records:
1. **Evidence Validity Classification**:
   - `VALID_INDEPENDENT`: Scored context, unassisted, fresh attempt on a distinct question ($W = 1.0$).
   - `HINT_DEGRADED`: Scored context, hint-assisted attempt with degraded evidence weight ($W_{\text{hint}} \le 0.35$).
   - `REPETITION_DISCOUNTED`: Repeat attempts on a previously attempted question ID contribute $0.0$ fresh independent weight.
   - `UNSCORED_PRACTICE`: Practice telemetry excluded from scored diagnostic certifications.
2. **Evidence Sufficiency Evaluation**:
   - Requires Evidence Confidence $C_k \ge 0.50$ and attempts across $\ge 2$ distinct questions to reach `SUFFICIENT`.
   - Sparse evidence or fewer than 2 distinct questions yields `INSUFFICIENT`, preventing ungrounded mastery or weakness determinations.
3. **Evidence Conflict Detection**:
   - Detects stark score variance ($\Delta \ge 0.50$) across independent questions under the same objective, assigning `CONFLICTING_EVIDENCE` until clarifying probes resolve the discrepancy.

### B. Bounded Diagnosis Engine & Misconception Analysis (`app/modules/adaptive_learning/diagnosis_engine.py`)
Enforces the frozen learning and diagnostic rules:
1. **Rule 1: Performance-Confidence Decoupling**:
   - Decouples ability estimate ($P_k \in [0.0, 1.0]$) from evidentiary certainty ($C_k \in [0.0, 1.0]$).
2. **Rule 2: Non-Catastrophic Diagnosis & Bounded Error Inferences**:
   - A single failed attempt **never** declares systemic weakness; if $C_k < 0.50$, the objective remains in `INSUFFICIENT_EVIDENCE`.
   - Rubric deduction patterns from `grading_provenance["deductions"]` are strictly classified:
     - `CANDIDATE_SIGNAL`: Observed only once or with low confidence; flagged as an unverified signal without assigning weakness.
     - `CONFIRMED_MISCONCEPTION`: Confirmed only when observed across $\ge 2$ distinct question attempts or supported by sufficient evidence.
3. **Rule 5: Hypothetical Prerequisites & Root-Cause Attribution**:
   - Evaluates prerequisite objective hypotheses along the curriculum DAG:
     - If child objective fails while a prerequisite is untested or weak, the diagnosis attributes root cause to `PREREQUISITE_HYPOTHESIS_DEFICIT` and routes to prerequisite remediation.
     - If all prerequisites are mastered, the diagnosis attributes root cause to `ISOLATED_CONCEPT_GAP`.
     - Failure in a child objective **never** retroactively imputes failure to parent prerequisites.
4. **Rule 7: Recovery Routing & Session Budget Ceiling**:
   - Capped session budget: Diagnostic probing is strictly bounded to $\le 5$ questions per session (`MAX_DIAGNOSTIC_SESSION_QUESTIONS = 5`) to prevent learner exhaustion.
   - If a student encounters persistent failure ($\ge 4$ failures with low scores), the engine triggers `GROUNDED_REVISION` rather than repeated testing loops.

### C. Service, Repository & REST API Integration
- **`app/services/diagnosis_service.py`**: Coordinates topological DAG traversals, computes course-wide summaries, and generates bounded session plans prioritizing prerequisite gaps and unverified evidence.
- **`app/schemas/diagnosis.py`**: Defines comprehensive Pydantic models for evidence ledgers, error signatures, prerequisite traces, and session plans.
- **`app/api/v1/endpoints/diagnosis.py`**:
  - `GET /api/v1/diagnosis/student/{student_id}/objective/{objective_id}`
  - `GET /api/v1/diagnosis/student/{student_id}/course/{course_id}`
  - `POST /api/v1/diagnosis/session/plan`

---

## 3. Verification & Test Evidence

### A. Backend Test Suite (`pytest -v`)
```
platform win32 -- Python 3.12.5, pytest-8.3.4, pluggy-1.6.0
collected 74 items

tests\contract\test_health_contract.py ...                               [  4%]
tests\integration\test_health_integration.py ..                          [  6%]
tests\integration\test_phase1_api.py ..........                          [ 20%]
tests\integration\test_phase2_mastery_api.py .                           [ 21%]
tests\integration\test_phase3_diagnosis_api.py .                         [ 22%]
tests\unit\test_config.py ..                                             [ 25%]
tests\unit\test_curriculum_validator.py ..............                   [ 44%]
tests\unit\test_dbms_engine.py .......                                   [ 54%]
tests\unit\test_dbms_grader.py ......                                    [ 62%]
tests\unit\test_diagnosis_engine.py ........                             [ 72%]
tests\unit\test_errors.py .....                                          [ 79%]
tests\unit\test_mastery_engine.py ........                               [ 90%]
tests\unit\test_phase1_models.py ...                                     [ 94%]
tests\unit\test_repositories.py ....                                     [100%]

============================= 74 passed in 5.24s ==============================
```

### B. Static Type Checking (`mypy app tests`)
```
Success: no issues found in 60 source files
```

### C. Linter & Formatting Checks (`ruff check app tests`)
```
All checks passed!
```

### D. Frontend Verification (`npm run typecheck` & `npm run build`)
```
> recall-frontend@0.1.0 typecheck
> tsc --noEmit
(Success - exit code 0)

> recall-frontend@0.1.0 build
> next build
   ▲ Next.js 15.5.27
   Creating an optimized production build ...
 ✓ Compiled successfully in 7.8s
   Linting and checking validity of types ...
   Collecting page data ...
 ✓ Generating static pages (4/4)
(Success - exit code 0)
```

### E. Static PostgreSQL DDL Generation (`alembic upgrade head --sql`)
Generated complete transactional DDL for all models and enums with exit code 0.

---

## 4. Retained Environmental Limitations

1. **Live PostgreSQL Credentials**: Live database migration against local PostgreSQL remains blocked by environment database credentials (`postgres:postgres@localhost:5432/recall`). SQLite in-memory engine with enforced foreign key pragmas (`PRAGMA foreign_keys=ON`) is utilized for automated verification.
2. **Multi-Connection Concurrency Testing**: True multi-connection concurrency tests remain deferred pending an available PostgreSQL test container or live connection. Transactional rollback and recovery logic has been statically and unit verified in `AttemptService`.

---

## 5. Scope and Git State

- **Branch**: `feature/phase-3-evidence-diagnosis`
- **Frozen Tags**:
  - `phase-0-frozen` (`fa1c70e`) — untouched
  - `phase-1-frozen` (`16895b7`) — untouched
  - `phase-2-frozen` (`e4a88ed`) — untouched
- **Phase 3 Commit Target**: `feature/phase-3-evidence-diagnosis`
- **Phase 3 Freeze Tag**: `phase-3-frozen`

---

## 6. Freeze Declaration

Phase 3 is complete, verified, and ready for freeze. All 74 tests pass, typechecks are clean, and no Phase 4 scope has been initiated.
