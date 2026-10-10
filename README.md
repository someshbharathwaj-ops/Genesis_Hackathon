# Recall

> **Institutional-grade grounded adaptive learning platform** with deterministic business authority, decoupled mastery and evidence confidence, and bounded language model execution.

---

## 🏛 System Architecture
Recall comprises three tightly coupled logical engines deployed as a high-performance modular monolith:
1. **Adaptive Learning Engine**: Authoritative deterministic grading, mastery estimation, diagnostic exploration, and review scheduling.
2. **Knowledge Engine**: Verified curriculum ingestion (PDF/PPT), slide metadata preservation, pgvector hybrid retrieval, and strict citation abstention.
3. **AI Execution Engine**: Bounded SLM adapter (Ollama/Qwen 2.5), strict JSON validation, circuit-breaker timeouts, and server-enforced tutor lockouts during scored assessments.

---

## 🚀 Quickstart & Local Setup

### 1. Backend Setup
```bash
cd backend
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements-dev.txt
cp ../.env.example .env
```

Run static checks and tests:
```bash
ruff check app tests
mypy app tests
pytest -v
```

Start backend development server:
```bash
uvicorn app.main:app --reload --port 8000
```
Open API docs: [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run typecheck
npm run dev
```
Open application: [http://localhost:3000](http://localhost:3000)

---

## 🛡 Strict Verification & Gated Phases
Every phase gate is validated with:
- Static analysis (`ruff`, `mypy`, `tsc`)
- Deterministic unit tests
- Schema contract tests
- RFC 7807 negative & integration tests
- Spaced regression test suites
