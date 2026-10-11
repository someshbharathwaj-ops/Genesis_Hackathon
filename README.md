# Recall

**A syllabus-grounded adaptive learning platform where code grades and tracks mastery, and a local small language model only explains.**

[![Branch: main](https://img.shields.io/badge/branch-main-22C55E?style=flat-square&logo=git)](https://github.com/someshbharathwaj-ops/Genesis_Hackathon/tree/main)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache_2.0-FF5A4F?style=flat-square)](LICENSE)
[![Tests: 141](https://img.shields.io/badge/tests-141-2BB8F0?style=flat-square)](backend/tests)
[![Local SLM: phi3:mini](https://img.shields.io/badge/local_SLM-phi3:mini_(Ollama)-FFC800?style=flat-square)](https://ollama.ai)

> **Use the `main` branch.** The other branches are frozen development milestones (see [Repository and branches](#8-repository-and-branches)).

---

## Table of contents

1. [Overview](#1-overview)
2. [Key features](#2-key-features)
3. [Architecture](#3-architecture)
4. [Technology stack](#4-technology-stack)
5. [The three engines](#5-the-three-engines)
6. [How Recall differs from a general-purpose LLM](#6-how-recall-differs-from-a-general-purpose-llm)
7. [Worked example: a 3NF decomposition question](#7-worked-example-a-3nf-decomposition-question)
8. [Repository and branches](#8-repository-and-branches)
9. [Getting started](#9-getting-started)
10. [Demo personas](#10-demo-personas)
11. [Testing](#11-testing)
12. [Status and limitations](#12-status-and-limitations)
13. [Intellectual property notice](#13-intellectual-property-notice)
14. [License](#14-license)
15. [Authors](#15-authors)

---

## 1. Overview

General-purpose language models are a poor fit for formal education when used as graders or tutors on their own:

- They can award different marks to the same answer on different attempts.
- They can cite sources that differ from the course's prescribed material.
- They can praise a wrong explanation.
- They can solve an exam question if a student pastes it in.

Recall addresses this by restricting what the language model is allowed to do.

### Core principle: zero generative scoring authority

> **[ADR 0002](docs/adr/0002-deterministic-adaptive-learning-engine.md):** language models never grade student work, compute marks or change mastery state. Their role is limited to bounded, course-grounded explanation and adversarial review. Grading, curriculum dependencies and knowledge-state tracking are computed by deterministic backend code.

In short: **the AI explains; deterministic code decides.**

---

## 2. Key features

| Area | What Recall does |
| :--- | :--- |
| **Grading** | Algebraic, rule-based grading of relational-database answers, with itemised deductions and hint penalties. |
| **Mastery tracking** | Bayesian Knowledge Tracing that keeps *performance* separate from *evidence confidence*. |
| **Diagnosis** | Walks a prerequisite graph to look for a possible root-cause gap, capped at 5 probe questions. |
| **Spaced review** | Retention-decay scheduler with a 1-hour cooldown against short-term recall. |
| **Grounded tutoring** | Answers drawn only from the course's uploaded material, with page or slide citations. |
| **Verification** | A three-role SLM pipeline (Generator, Evidence Reviewer, Adversarial Challenger) arbitrated by a non-voting controller. |
| **Exam integrity** | Server-side HTTP 403 lockout of the Tutor and Revisor during scored attempts. |
| **Course isolation** | Retrieval filters on `course_id`, so one course's material is never returned for another. |
| **Local execution** | Runs on local hardware through Ollama, with no external cloud API dependency. |

---

## 3. Architecture

Recall is a **modular monolith**: one backend application with three domain engines behind a FastAPI gateway.

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                            FRONTEND (Next.js 15)                            │
│        React 19 · TypeScript · Tailwind CSS · Recall Tactile design         │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ REST · RFC 7807 errors · HMAC-SHA256 JWT
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                        BACKEND GATEWAY (FastAPI / ASGI)                     │
│   Python 3.12 · Pydantic v2 · Uvicorn · SQLAlchemy (async) · Alembic        │
├─────────────────────────────────────────────────────────────────────────────┤
│  1. ADAPTIVE LEARNING ENGINE (ALE)     rule-based, no language model        │
│     relational engine · grader · mastery (BKT) · diagnosis · scheduler      │
│  2. KNOWLEDGE ENGINE (KE)                                                   │
│     document ingestion · provenance-preserving chunking · isolated search   │
│  3. AI EXECUTION ENGINE (AEE)                                               │
│     SLM triad · prompt assembler and sanitizer · assessment lockout guard   │
└──────────────────────┬───────────────────────────────┬──────────────────────┘
                       │                               │
┌──────────────────────▼──────────────┐ ┌──────────────▼──────────────────────┐
│     DATABASE AND VECTOR STORAGE     │ │    LOCAL INFERENCE (Ollama)         │
│ SQLite (dev) / PostgreSQL + pgvector│ │ phi3:mini (3.8B) · nomic-embed-text │
└─────────────────────────────────────┘ └─────────────────────────────────────┘
```

---

## 4. Technology stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| Frontend | Next.js 15 (App Router), React 19, TypeScript | Student, instructor and admin interfaces. |
| Styling | Tailwind CSS with the Recall Tactile design system | Warm off-white canvas (`#FFFBF2`), near-black ink (`#17171A`), hard offset shadows (`0 4px 0 #17171A`), high-contrast buttons. |
| Backend API | FastAPI, Python 3.12, Uvicorn | Asynchronous endpoints under `/api/v1`. |
| Validation | Pydantic v2 | Request and response validation and serialisation. |
| Database | SQLite (local demo) / PostgreSQL + pgvector | Users, courses, learning objectives, versioned questions, attempts, audit logs, review queues, vectors. |
| ORM and migrations | SQLAlchemy 2.0 (async), Alembic | Typed queries and reversible schema migrations. |
| Security | HMAC-SHA256 JWT, RFC 7807 problem details | Role-based route guards (`student`, `instructor`, `admin`) and standard error responses. |
| Language model | Ollama serving `phi3:mini` (3.8B) | Local inference at temperature 0.2 with a 1024-token budget. |
| Embeddings | `nomic-embed-text`, cosine similarity | Course-isolated semantic search. |
| Testing | Pytest | 108 unit tests and 33 integration tests. |

---

## 5. The three engines

### 5.1 Adaptive Learning Engine (ALE)

The ALE contains no language model. Source: `backend/app/modules/adaptive_learning/`.

**Relational engine** (`dbms_engine.py`)
- Attribute closure (X⁺) using Armstrong's axioms with fixpoint iteration.
- Candidate-key discovery by minimal-subset search with superset pruning.
- Minimal cover: right-hand-side decomposition, removal of extraneous left-hand attributes and redundant dependencies.
- Normal-form checks for 1NF, 2NF (partial dependencies), 3NF (transitive non-prime dependencies) and BCNF (superkey violations).
- Chase-matrix test for lossless join, plus dependency-preservation checks.

**Grader** (`dbms_grader.py`)
- Compares answers algebraically rather than by text similarity.
- Awards partial credit and reports the reason, for example `EXTRANEOUS_KEY_ATTRIBUTE` when `{Emp_ID, Dept_ID}` is submitted but only `{Emp_ID}` is a minimal key.
- Applies a hint penalty (hint weight ≤ 0.35 per hint requested) so hints cannot inflate marks.

**Mastery engine** (`mastery_engine.py`)
- Bayesian Knowledge Tracing that separates **performance** P ∈ [0, 1] from **evidence confidence** C ∈ [0, 1].
- A single mistake after strong earlier evidence flags `INSUFFICIENT_EVIDENCE` and triggers targeted probing instead of an immediate drop in mastery.

**Diagnosis engine** (`diagnosis_engine.py`)
- Walks the learning-objective graph backwards. If a student fails `LO_NORMALIZATION`, it probes whether the root gap is in `LO_KEYS` or `LO_CLOSURE`.
- Limits a diagnostic session to **5 probe questions**.

**Scheduler** (`scheduling_engine.py`)
- Models retention decay as R(t) = exp(−Δt / S).
- **Rule 6, working-memory cooldown:** a concept tested within the last 60 minutes is kept out of the durable spaced-review queue, so review measures retention rather than immediate recall.

### 5.2 Knowledge Engine (KE)

Source: `backend/app/modules/knowledge_engine/`.

- **Extraction** (`document_extractor.py`): `.pdf`, `.docx`, `.pptx`, `.txt` and `.md`, with SHA-256 hashing for deduplication.
- **Chunking** (`chunker.py`): every chunk carries file hash, document title, slide or page number and section title.
- **Course isolation:** vector queries filter on `course_id`. A question asked in `CS340 Database Management Systems` cannot retrieve excerpts from `CS301 Operating Systems`.

### 5.3 AI Execution Engine (AEE)

Source: `backend/app/modules/ai_engine/`.

| Role | File | Responsibility |
| :--- | :--- | :--- |
| **A. Generator / Tutor** | `tutor_engine.py` | Writes explanations from retrieved course passages only. Detects the query type (normalisation problem, formula, algorithm trace, short factual question) and formats the answer to match. |
| **B. Evidence Reviewer** | `revisor_engine.py` | Checks each sentence against the retrieved excerpts to catch ungrounded claims. |
| **C. Adversarial Challenger** | `revisor_engine.py` | Looks for logical counterexamples and edge cases. |
| **Verification Controller** | deterministic | Releases an answer only if citation review passes. Mathematical claims (for example a 3NF decomposition) are re-checked by the ALE. If the notes lack evidence, the system **abstains** instead of guessing. It does not use majority voting. |
| **Assessment lockout guard** | API layer | During an active scored attempt, any Tutor or Revisor call is rejected with HTTP `403 AssessmentLockoutError`. |

The prompt assembler builds course-grounded prompts, and a response sanitizer removes placeholder tokens before output reaches the student.

---

## 6. How Recall differs from a general-purpose LLM

| Dimension | General-purpose LLM tutor | Recall |
| :--- | :--- | :--- |
| **Grading** | Marks come from generated text and can vary between attempts. | Marks come from algebraic code. The same answer gives the same marks. |
| **Grounding** | Draws on broad training data, which may differ from the course syllabus. | Restricted to the instructor's uploaded material, with citations such as `[Lecture: Chapter10-normalization.pdf, Page 39]`. |
| **Missing evidence** | May produce a confident answer anyway. | Designed to state that the course material does not cover the question. |
| **Learner state** | No persistent model of what a student knows. | Persistent knowledge state across a prerequisite graph, with performance and confidence kept separate. |
| **Exam integrity** | Will answer pasted exam questions. | Server-side lockout during scored attempts. |
| **Data and cost** | Queries and course material go to an external provider; cost scales with tokens. | Runs locally through Ollama; no per-token cost and no external API dependency. |
| **Use** | Students must write careful prompts. | Students ask natural questions; prompt assembly happens in the backend. |

---

## 7. Worked example: a 3NF decomposition question

**Question shown to the student**

> Schema: `EMPLOYEE_DEPT (Emp_ID, Emp_Name, Dept_ID, Dept_Name)`
> Dependencies: `Emp_ID → Emp_Name`, `Emp_ID → Dept_ID`, `Dept_ID → Dept_Name`
> Is it in 3NF? Convert it if not.

**Flow**

1. The student submits: `EMPLOYEE(Emp_ID, Emp_Name, Dept_ID)` and `DEPARTMENT(Dept_ID, Dept_Name)`.
2. **Deterministic evaluation:** `dbms_grader.py` parses the tables and `dbms_engine.py` computes the result.
   - Candidate key: `{Emp_ID}`.
   - 3NF violation: `Dept_ID → Dept_Name` is a transitive dependency on a non-prime attribute.
   - Lossless join: the intersection `{Dept_ID}` is a superkey of `DEPARTMENT`, so the join is lossless.
   - Dependency preservation: all three dependencies are preserved.
   - Score: 100%, stored in the attempt ledger.
3. **Mastery update:** Bayesian Knowledge Tracing updates the estimate for `LO_NORMALIZATION`, and the scheduler applies the 1-hour cooldown before the question can enter durable review.
4. **Conceptual help:** the student asks, "Why does `Dept_ID → Dept_Name` violate 3NF?" The Knowledge Engine retrieves passages from `Chapter10-normalization.pdf`, the SLM drafts an explanation, the review roles check it against those passages, and the student sees the explanation with citations.
5. **Interface:** a correct-submission badge, the updated mastery score, the cited explanation and a practice-mode indicator.

---

## 8. Repository and branches

**Always use `main`.**

```bash
git checkout main
```

Recall was built in gated phases (0 to 7). The other branches are historical milestones, each frozen with a Git tag:

- `feature/phase-0-foundation` through `feature/phase-7-frontend-auth` (tags `phase-0-frozen` to `phase-7-frozen`)
- `fix/phase-7-security-contracts`
- `phase-8-release-readiness`

All feature work, fixes, content expansion and Tutor improvements have been consolidated into `main`.

---

## 9. Getting started

### Prerequisites

- Git
- Python 3.12 or newer
- Node.js 18 or newer, and npm
- [Ollama](https://ollama.ai), installed and running

### Step 1: Clone and check out `main`

```bash
git clone https://github.com/someshbharathwaj-ops/Genesis_Hackathon.git
cd Genesis_Hackathon
git checkout main
```

### Step 2: Pull the local models

```bash
ollama pull phi3:mini
ollama pull nomic-embed-text
```

### Step 3: Start the backend

```bash
cd backend

# Windows (PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Linux / macOS
python -m venv .venv
source .venv/bin/activate

pip install -r requirements-dev.txt

# Optional: explicit environment file (the backend has default fallbacks)
#   Windows:       Copy-Item ../.env.example .env
#   Linux / macOS: cp ../.env.example .env

# Seed courses, syllabus material and question banks
python scripts/validate_and_ingest_content.py

uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Verify the backend:

- Health probe: <http://127.0.0.1:8000/api/v1/healthz> (returns `{"status":"healthy"}`)
- Swagger documentation: <http://127.0.0.1:8000/api/v1/docs>

### Step 4: Start the frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:3000>.

---

## 10. Demo personas

The navigation bar includes one-click demo logins.

| Persona | Account | What to try |
| :--- | :--- | :--- |
| **Student: Ada Lovelace** | `student.ada@recall.edu` | Solve normalisation and candidate-key problems and see itemised deductions and hint penalties. View the learning graph (`LO_CLOSURE` → `LO_KEYS` → `LO_NORMALIZATION`). Ask the grounded Tutor (for example, "Is relation EMPLOYEE_DEPT in 3NF?"). Open the spaced-review queue. Start an `independent_checkpoint` to see the 403 lockout block the Tutor. |
| **Instructor: Prof. E. F. Codd** | `instructor.dbms@recall.edu` | Upload `.pdf`, `.docx`, `.pptx` or `.md` lecture material (SHA-256 deduplication, vector indexing). Schedule quizzes with dates and passing thresholds; enrolled students see them on their assessment calendar. |
| **Administrator: Audit Officer** | `admin.audit@recall.edu` | Inspect audit logs, role-authorisation events and multi-course seed controls. |

---

## 11. Testing

```bash
cd backend

# 108 unit tests
pytest tests/unit -v

# 33 integration tests (role authorisation, scheduling, assessment lockout)
pytest tests/integration -v

# Frontend type checking and production build
cd ../frontend
npm run build
```

---

## 12. Status and limitations

- **Model size.** The language model is a 3.8B-parameter local model. The review and challenge roles and the controller reduce unsupported claims but cannot eliminate them.
- **Evaluation.** The effect of Recall on learning outcomes has not been evaluated in a controlled study.
- **Content coverage.** Grading is implemented for relational-database problems (closures, keys, normal forms, decompositions). Other subjects depend on the material and question banks that are ingested.
- **Development database.** SQLite is used for the local demo. PostgreSQL with pgvector is the intended deployment database.
- **Local inference.** Running models locally trades per-token cost and data exposure for hardware requirements and slower responses.

---

## 13. Intellectual property notice

<!-- Confirm patent-filing status before publishing; remove or reword this section if no application has been filed. -->

Certain architectures, algorithms and workflows in this repository are the subject of patent applications and proprietary rights held by the inventors, including:

1. **Deterministic relational grading and knowledge-state tracing:** non-generative assessment evaluation using fixpoint Armstrong closures, Chase tableau matrices and Bayesian Knowledge Tracing with decoupled evidence-confidence metrics.
2. **Multi-role collaborative SLM verification:** bounded local language-model execution with role-differentiated generation (Tutor), evidence auditing (Reviewer) and adversarial probing (Challenger), arbitrated by a non-voting deterministic verification controller.
3. **Server-side assessment lockout state machine:** API-gateway enforcement of assessment lockouts against generative AI assistance through persistent attempt-lifecycle states.

---

## 14. License

Licensed under the **Apache License, Version 2.0**. See [LICENSE](LICENSE) or <http://www.apache.org/licenses/LICENSE-2.0>.

Apache 2.0 includes an express patent grant (Section 3) and permits use, reproduction and derivative works for academic, evaluation and open-source purposes.

```text
Copyright 2026 Somesh Bharathwaj, Nandina Ankers, Nishitha Gowri, Niranjan Reddy

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```

---

## 15. Authors

Somesh Bharathwaj, Shri Nanthana R P, Nishitha Gowri and Niranjan Reddy.