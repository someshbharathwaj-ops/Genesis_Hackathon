# Recall — Phase 7 Engineering & Freeze Report
**Branch:** `feature/phase-7-frontend-auth`  
**Base Commit:** `d4c0ad8` (`phase-6-frozen`)  
**Scope:** Phase 7 — Frontend UI and Authentication Integration  

---

## 1. Executive Summary

Phase 7 connects Recall's complete backend modular architecture into a coherent, demo-ready, responsive Next.js application strictly upholding the repository's core invariants:
- **Zero Generative Grading Authority (ADR 0002):** The frontend delegates all assessment scoring, mastery updates, and diagnostic routing to deterministic backend engine logic.
- **Server-Side Authorization & Identity Protection:** Implemented an RFC 7807 compliant HMAC-SHA256 Bearer JWT authentication mechanism. Client-supplied student IDs are never trusted blindly; route guards and backend dependencies enforce active enrollment and role isolation.
- **Assessment Lockout Visibility:** Active scored checkpoints (`independent_checkpoint`) immediately engage server-side lockouts (`403 AssessmentLockoutError`), cleanly disabling free-form AI Tutor and Revisor assistance.
- **Design System Fidelity:** Built with Recall's tactile palette—warm off-white `#FFFBF2`, near-black `#17171A`, sunshine yellow `#FFC800`, coral `#FF5A4F`, green `#22C55E`, and cyan `#2BB8F0`—featuring tactile borders, hard drop shadows, and high-contrast typography without generic AI SaaS templates or glassmorphism.

---

## 2. Implemented Architecture & Contracts

### 2.1 Server-Side Authentication & Session Management
- **Token Format:** URL-safe HMAC-SHA256 signed JWT (`base64url(header).base64url(payload).base64url(sig)`), signed with `settings.SECRET_KEY` without requiring external binary dependencies (`app/core/security.py`).
- **Authorization Dependencies (`app/core/auth.py`):**
  - `get_current_user`: Validates header `Authorization: Bearer <token>`, decodes claims, verifies signature and expiration, and fetches the active `User` record from the database.
  - `verify_student_ownership`: Rejects unauthorized cross-student queries (`403 Forbidden`).
  - `verify_course_enrollment`: Ensures students are actively enrolled in the requested course (`403 Forbidden`).
- **Endpoints (`app/api/v1/endpoints/auth.py`):**
  - `POST /api/v1/auth/login`: Authenticate existing user by email and issue token.
  - `POST /api/v1/auth/demo-login`: Instant demo login for hackathon evaluation (`student.ada@recall.edu` or `instructor.dbms@recall.edu`), automatically ensuring CS340 course enrollment.
  - `GET /api/v1/auth/me`: Retrieve current profile and active course enrollments.
  - `POST /api/v1/auth/enroll`: Self-enrollment for active students.

### 2.2 Next.js App Router Client Architecture
- **API Client (`frontend/src/lib/api-client.ts`):** Centralized, type-safe API client managing Bearer token injection, RFC 7807 problem details error handling, and complete endpoint bindings across all phases.
- **Shared Types (`frontend/src/types/index.ts`):** Complete TypeScript definitions mirroring backend Pydantic schemas for Identity, Curriculum, Questions, Attempts, Documents, Retrieval, Mastery, Bounded Diagnosis, Tutor, Revisor, and Spaced Scheduling.

---

## 3. Seven Core Learning Journeys

1. **Authentication & Identity Switching (`Navbar.tsx`):**
   - Seamless one-click demo login for **Ada Lovelace (Student)** and **Prof. E. F. Codd (Instructor)**.
   - Shows active user badge, course switcher, and live Assessment Lockout status banner.
2. **Course Catalog & Curriculum DAG (`CurriculumTab.tsx`):**
   - Course summary cards with topic breakdown.
   - Interactive Learning Objectives list with prerequisite dependency tags (e.g., `LO_KEYS` requires `LO_CLOSURE`).
   - Verified Question Bank inspector displaying difficulty and authoritative verification credentials.
3. **Knowledge Engine & Course Materials (`KnowledgeTab.tsx`):**
   - File uploader supporting `.pdf` and `.txt` materials with repeat-safe content hashing.
   - Ingested document catalog with page/chunk counts and status tags.
   - Semantic vector retrieval sandbox demonstrating tenant-isolated chunk search with page provenance (`[Lecture: dbms_lecture1.txt, Page 1]`).
4. **Student Mastery & Bounded Diagnosis (`MasteryDiagnosisTab.tsx`):**
   - Live Course Mastery Index and objective-level Bayesian Knowledge Tracing $P(L)$ confidence bounds.
   - Bounded Diagnostic Evaluation: `CONFIRMED_MASTERY`, `CONFIRMED_GAP`, `UNTESTED`, `INSUFFICIENT_EVIDENCE`.
   - Prerequisite dependency failure tracking and bounded diagnostic probing session generator ($\le 5$ questions).
5. **Interactive Practice & Assessment Lockout (`PracticeTab.tsx`):**
   - Practice and checkpoint question runner with expression/closure answer input.
   - Immediate deterministic grading display: points earned, correct/incorrect status, and rubric audit provenance.
   - Toggle to simulate active scored assessments (`independent_checkpoint`) to demonstrate the live AI Tutor & Revisor lockout in action!
6. **Grounded AI Tutor - SLM Role A (`TutorTab.tsx`):**
   - Syllabus-grounded concept explanation query runner with candidate excerpts.
   - Source citations clickable pill list (`[Lecture: dbms_lecture1.txt, Page 1]`).
   - Explicit, honest abstention banner when out-of-syllabus questions are asked.
   - Live 403 `ASSESSMENT_LOCKOUT` warning display when active scored attempt is running.
7. **Grounded Revisor & Adversarial Audits - SLM Role B (`RevisorTab.tsx`):**
   - Cross-examines candidate explanations and misconceptions against course evidence.
   - Audit verdicts: `VERIFIED_GROUNDED`, `UNGROUNDED_CLAIM_DETECTED`, `DETERMINISTIC_CONTRADICTION`, and `INSUFFICIENT_EVIDENCE`.
   - ADR 0002 deterministic relational-closure contradiction override demonstration.
8. **Spaced Retention Scheduling & Rule 6 Cooldown (`SchedulingTab.tsx`):**
   - Real-time review queue prioritized by exponential retention decay $R(t) = \exp(-\Delta t / S)$.
   - Rule 6 working-memory cooldown boundary indicator: items tested within 1 hour display a locked cooldown countdown and are excluded from durable review sessions.
   - Bounded retention review session plan generator (context: `retention_review`, $\le 5$ questions).

---

## 4. Verification Suite Results

### 4.1 Backend Automated Tests (Pytest)
```
121 passed in 13.54s
```
- Total test suites: 10 unit suites + 7 integration suites.
- Coverage includes all Phase 0–6 regression tests + new Phase 7 auth security unit tests (`test_auth_security.py`) and integration tests (`test_phase7_auth_api.py`).

### 4.2 Code Quality & Static Analysis
- **Ruff Check:** Clean across `backend/app` and `backend/tests` (`All checks passed!`).
- **Mypy Static Type Checking:** `Success: no issues found in 73 source files`.
- **Alembic Migrations:** Verified via static SQL generation (`alembic upgrade --sql base:head`); zero new schema migrations required.

### 4.3 Frontend Typecheck & Production Build
- **TypeScript Typecheck:** `tsc --noEmit` exited cleanly with code 0.
- **Next.js Production Build:** `next build` compiled all routes and prerendered static pages cleanly (`Route (app) 17.5 kB`).

---

## 5. Hackathon Demo Walkthrough Instructions

1. **Start Backend Server:**
   ```bash
   cd backend
   .venv\Scripts\python.exe -m uvicorn app.main:app --port 8000 --reload
   ```
2. **Start Frontend Dev Server:**
   ```bash
   cd frontend
   npm run dev
   ```
3. **Open Browser:** Navigate to `http://localhost:3000`.
4. **Step-by-step Demo Flow:**
   - **Identity & Seeding:** Click **"Seed DBMS"** in the top navigation to seed the CS340 course, curriculum DAG, and 10+ verified questions. Note the active user is automatically authenticated as **Ada Lovelace (Student)** with a valid Bearer token.
   - **Curriculum Inspection:** Under the **"Curriculum & Overview"** tab, inspect topic `FD_NORM` and its 5 learning objectives. Select `LO_KEYS` to see prerequisite `LO_CLOSURE`.
   - **Knowledge Material:** Under **"Knowledge & Materials"**, view the course lecture document or upload a new PDF/TXT file. Test the **Vector Knowledge Retrieval Sandbox** with *"Armstrong axioms transitivity"* to inspect retrieved chunks and page numbers.
   - **Interactive Practice:** Under **"Practice & Lockout"**, select a question, enter `A, B, C, D`, and click **"Submit for Evaluation"**. Observe the instantaneous deterministic grading provenance.
   - **Lockout Demonstration:** Click **"Simulate Active Scored Lockout"** (or submit with context `independent_checkpoint`). Notice the header alert illuminates: **"ASSESSMENT LOCKOUT ACTIVE: AI Assistance Disabled (ADR 0002)"**.
   - **Tutor Lockout Check:** Switch to **"AI Tutor (SLM A)"**. Attempt to ask a question. Observe the HTTP 403 server lockout banner blocking unauthorized generative exam assistance.
   - **Revisor Adversarial Challenge:** Under **"Revisor Audit (SLM B)"**, select preset **"Contradiction"** (*"closure {A}+ does not contain {B} or {C}"*). Click **"Run Revisor Audit"**. Notice the **DETERMINISTIC_CONTRADICTION** verdict with **OVERRIDE APPLIED** tag, proving mathematical rules override model consensus!
   - **Spaced Retention (Rule 6):** Under **"Spaced Scheduling"**, view the prioritized review queue. Notice recently attempted items display **"Cooldown (3600s)"** honoring Rule 6 working memory boundaries. Click **"Plan Spaced Session"** to generate a bounded retest plan.

---

## 6. Known Limitations & Phase 8 Handover

- **Production Storage:** File uploads currently default to the local filesystem (`./uploads`) with content-hashed deduplication. Cloud object storage (S3/GCS) can be configured for multi-node deployments.
- **Model Adapter:** Verified against Ollama `qwen2.5:3b` and `DeterministicMockLanguageModelProvider` for offline deterministic verification.
- **Next Phase:** Phase 8 is reserved for final polish, production containerization/deployment, or hackathon pitch submission as explicitly authorized.
