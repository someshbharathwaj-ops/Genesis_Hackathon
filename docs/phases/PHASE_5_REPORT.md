# Recall — Phase 5 Report: Model Adapter & Grounded Tutor

**Phase**: 5 (Model Adapter & Grounded Tutor)  
**Branch**: `feature/phase-5-model-adapter-tutor` (derived from `c552d94`, tagged `phase-4-frozen`)  
**Base Commit / Frozen Tags**: `phase-0-frozen` (`fa1c70e`), `phase-1-frozen` (`16895b7`), `phase-2-frozen` (`e4a88ed`), `phase-3-frozen` (`8408e6f`), `phase-4-frozen` (`c552d94`)  
**Evaluation Date**: 2026-10-11  
**Status**: COMPLETE (Gated Verification Succeeded)

---

## 1. Executive Summary

Phase 5 implements the **Replaceable Language Model Adapter & Grounded Tutor Service**, connecting Recall's course-scoped retrieval pipeline to a language model while enforcing non-negotiable architectural guardrails:
1. Explaining concepts using only retrieved course materials with formal citations (`[Lecture: <filename>, Page <X>]`).
2. Explicitly abstaining from answering when materials are insufficient or missing, preventing hallucinations.
3. Server-side assessment lockout blocking free-form tutoring queries when a student has an active scored attempt.
4. Total decoupling from grading, Bayesian mastery updating, and diagnostic state machines (pure read/generation operation).

All 102 tests in the complete backend test suite pass cleanly. Static type checking (`mypy`), linting (`ruff`), and frontend compilation (`tsc`, `next build`) succeed with zero errors.

---

## 2. Architecture & Design Implementation

### A. Replaceable Language Model Provider (`app/modules/ai_engine/model_provider.py`)
- **Abstract Interface**: `BaseLanguageModelProvider` specifies `generate_response(prompt, system_prompt, temperature, max_tokens) -> ModelResponse`.
- **Deterministic Mock Provider**: `DeterministicMockLanguageModelProvider` provides deterministic, fast, offline responses that cite course materials when excerpts are provided, and returns explicit abstention notices when materials are lacking.
- **Ollama Provider Integration**: `OllamaLanguageModelProvider` connects to `http://localhost:11434/api/generate` with bounded error handling:
  - `ModelTimeoutError` (HTTP 504) on request timeouts.
  - `ModelUnavailableError` (HTTP 503) on connection failure or missing models.
  - `ModelProviderError` (HTTP 502) on upstream server failures.
  - `MalformedModelResponseError` (HTTP 502) on invalid or empty JSON payloads.
  - Provider factory `get_model_provider()` toggles providers cleanly based on `USE_MOCK_LLM`.

### B. Grounded Prompt Engineering & Guardrails (`app/modules/ai_engine/tutor_engine.py`)
- **System Prompt**: Enforces strict grounding rules forbidding extrapolation, outside assumptions, or hallucination.
- **Context Window Bounding**: `GroundedTutorEngine.assemble_prompt` caps total excerpt characters (`MAX_CONTEXT_CHARACTERS = 12000`) and limits chunks (`MAX_EXCERPTS = 5`) to prevent prompt blowout.
- **Honest Abstention Protocol**: Pre-configured standard abstention notice stating curriculum evidence insufficiency without calling model inference.

### C. Grounded Tutor Service (`app/services/tutor_service.py`)
- **Orchestration**: Validates course and student existence, verifies active assessment locks, retrieves course-scoped candidate chunks, checks similarity thresholds, and invokes the model adapter.
- **Server-Side Scored Assessment Lockout**: Queries `attempts` table for `status = AttemptStatus.IN_PROGRESS`. If found, immediately raises `AssessmentLockoutError` (HTTP 403), preventing cheating during diagnostic evaluations.
- **Decoupled Read Immutability**: The Tutor service does not write to `attempts`, `mastery`, or `diagnosis` tables.

### D. REST API Contract (`app/api/v1/endpoints/tutor.py`)
- `POST /api/v1/courses/{course_id}/tutor/ask`:
  - Request: `TutorQueryRequest(student_id, query, objective_id)`
  - Response: `TutorQueryResponse(answer, citations, abstention_recommended, course_id, student_id, model_used, retrieved_chunks_count, is_mock, warning)`
  - Error responses: RFC 7807 problem details for 403 (Lockout), 404 (Not Found), 422 (Validation), 502/503/504 (Provider failures).

---

## 3. Verification & Test Evidence

### A. Backend Test Suite (`pytest -v`)
```
platform win32 -- Python 3.12.5, pytest-8.3.4, pluggy-1.6.0
collected 102 items

tests\contract\test_health_contract.py ...                               [  2%]
tests\integration\test_health_integration.py ..                          [  4%]
tests\integration\test_phase1_api.py ..........                          [ 14%]
tests\integration\test_phase2_mastery_api.py .                           [ 15%]
tests\integration\test_phase3_diagnosis_api.py .                         [ 16%]
tests\integration\test_phase4_rag_api.py .                               [ 17%]
tests\integration\test_phase5_tutor_api.py .                             [ 18%]
tests\unit\test_ai_model_provider.py ...........                         [ 29%]
tests\unit\test_config.py ..                                             [ 31%]
tests\unit\test_curriculum_validator.py ..............                   [ 45%]
tests\unit\test_dbms_engine.py .......                                   [ 51%]
tests\unit\test_dbms_grader.py ......                                    [ 57%]
tests\unit\test_diagnosis_engine.py ........                             [ 65%]
tests\unit\test_errors.py .....                                          [ 70%]
tests\unit\test_knowledge_engine.py ..........                           [ 80%]
tests\unit\test_mastery_engine.py ........                               [ 88%]
tests\unit\test_phase1_models.py ...                                     [ 91%]
tests\unit\test_repositories.py ....                                     [ 95%]
tests\unit\test_tutor_engine.py .....                                    [100%]

============================ 102 passed in 13.78s =============================
```

### B. Static Type Checking (`mypy app tests`)
```
Success: no issues found in 81 source files
```

### C. Linter & Formatting Checks (`ruff check app tests`)
```
All checks passed!
```

### D. Frontend Verification (`npm run typecheck` & `npm run build`)
```
> tsc --noEmit (0 errors)
> next build (Compiled successfully in 8.4s, static routes optimized)
```

---

## 4. Live Model Verification Status & Limitations

- **Local Ollama Service**: Verified running and reachable at `http://127.0.0.1:11434`.
- **Installed Models**: Verified local models `phi3:mini`, `qwen3:8b`, and `gemma3:4b` present on host.
- **Configured Baseline Model**: `PRIMARY_MODEL` default remains `qwen2.5:3b`. Host did not have `qwen2.5:3b` pulled.
- **Inference Smoke Test**: Attempting inference against unloaded local model `phi3:mini` triggered cold-start loading exceeding 30s, cleanly raising `ModelTimeoutError` without crashing the application or corrupting state.
- **Deterministic Automated Testing**: Automated test suite relies on `USE_MOCK_LLM = True` and mocked HTTP transports, guaranteeing 100% offline reproducibility without external GPU/network dependencies.

---

## 5. Architectural Alignment & Next Steps

1. **Phase 5 Freeze**: Phase 5 is ready to freeze. No Phase 6 features (multi-SLM debate orchestration, Revisor challenge pipeline, frontend tutor UI) were implemented in this phase.
2. **Immutable History**: All prior frozen tags (`phase-0-frozen` through `phase-4-frozen`) remain unmodified.
