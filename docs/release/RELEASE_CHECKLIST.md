# Recall: Production Release Checklist & Preflight Verification

**Version:** 1.0.0-final  
**Release Target:** Institutional Hackathon Demonstration & Deployment  
**Repository:** `someshbharathwaj-ops/Genesis_Hackathon`  
**Primary Branch:** `main`

---

## 1. Safety & Milestone Invariants Preflight

- [x] **Frozen Phase Milestones Intact:**
  - [x] Phase 0 (`fa1c70e`): `phase-0-frozen`
  - [x] Phase 1 (`16895b7`): `phase-1-frozen`
  - [x] Phase 2 (`e4a88ed`): `phase-2-frozen`
  - [x] Phase 3 (`8408e6f`): `phase-3-frozen`
  - [x] Phase 4 (`c552d94`): `phase-4-frozen`
  - [x] Phase 5 (`876d05f`): `phase-5-frozen`
  - [x] Phase 6 (`d4c0ad8`): `phase-6-frozen`
  - [x] Phase 7 (`b87aad8`): `phase-7-frozen`
- [x] **No History Rewrites:** No `git reset --hard` or forced history manipulation executed.
- [x] **Linear Milestone Ancestry:** All frozen tags are ancestors of the unified `main` branch.

---

## 2. Security & Credentials Hygiene

- [x] **Secret Exclusion:** `.env`, private keys, and session tokens are strictly ignored by `.gitignore`.
- [x] **Safe Template Preserved:** `.env.example` provides explicit default ports and mock flags.
- [x] **Database & Binary Cache Exclusion:** `*.db`, `*.sqlite`, `*.pyc`, `__pycache__`, `.next/`, and `node_modules/` are untracked.
- [x] **Server-Side Authorization:**
  - [x] Role-based access control gates `/api/v1/admin/*` endpoints strictly to users with role `admin`.
  - [x] Student ownership verification prevents unauthorized cross-student data access.
  - [x] Scored assessment checkpoints enforce server-side lockout (`403 AssessmentLockoutError`), preventing tutor and revisor bypass.

---

## 3. Engine Integrity & Automated Testing

- [x] **Backend Unit Suite:** 108/108 tests passing (`pytest tests/unit`).
  - [x] Adaptive Learning Engine: Armstrong axioms, attribute closure, candidate keys, minimal cover, 1NF/2NF/3NF/BCNF, Chase lossless join, dependency preservation.
  - [x] Deterministic DBMS Grader: Zero generative scoring authority (ADR 0002).
  - [x] Mastery Engine: BKT state persistence, hint discounts, repetition discounts.
  - [x] Knowledge Engine: Document hashing, chunking, tenant-isolated vector retrieval.
  - [x] Grounded Tutor & Revisor: Adaptive prompt assembly, zero template leakage, citation enforcement, honest abstention.
- [x] **Backend Integration Suite:** 33/33 tests passing (`pytest tests/integration`).
  - [x] Role authorization and audit logging.
  - [x] Scheduled assessment creation and student notification feed.
  - [x] Auth token lifecycle and student enrollment.
- [x] **Frontend Production Build:** Next.js 15 App Router (`npm run build`) compiles with zero TypeScript errors or broken imports.

---

## 4. Student & Teacher User Experience (UX)

- [x] **Natural Terminology:** Zero references to internal AI jargon ("inquiry prompt", "prompt engineering") in student UI. Students "Ask a question", receive an "Answer", view "Course Sources", and solve "Questions".
- [x] **One-Click Role Switcher:** Fast switching between Student (`student.ada@recall.edu`), Instructor (`instructor.dbms@recall.edu`), and Admin (`admin.audit@recall.edu`) for evaluators.
- [x] **Assessment Lockout Visibility:** Visual alert banner clearly states when AI tutoring is restricted during exams.
- [x] **Persistent Assessment Notifications:** Teacher-scheduled quizzes immediately notify enrolled students and render on their upcoming assessment calendar.

---

## 5. Deployment Instructions

1. **Start Backend:**
   ```bash
   cd backend
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
2. **Start Frontend:**
   ```bash
   cd frontend
   npm run dev
   ```
3. **Verify Health Endpoint:**
   `GET http://127.0.0.1:8000/api/v1/healthz` returns `{"status": "healthy"}`.
4. **Access Web Application:**
   Open browser at `http://localhost:3000`. Click "Demo Student Login" to begin evaluation.
