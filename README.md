# Recall: Grounded Adaptive Learning Platform

[![Branch: main](https://img.shields.io/badge/Branch-main_(Production)-22C55E?style=for-the-badge&logo=git)](https://github.com/someshbharathwaj-ops/Genesis_Hackathon/tree/main)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-FF5A4F?style=for-the-badge)](LICENSE)
[![Tests: 141 Passing](https://img.shields.io/badge/Automated_Tests-141_Passing-2BB8F0?style=for-the-badge)](backend/tests)
[![SLM: phi3:mini](https://img.shields.io/badge/Local_SLM-phi3:mini_(Ollama)-FFC800?style=for-the-badge)](https://ollama.ai)

> **Institutional-grade adaptive learning platform** with deterministic relational grading authority, Bayesian Knowledge Tracing with decoupled confidence, course-isolated syllabus grounding, and a bounded local Small Language Model (SLM) verification pipeline.

---

## 📌 Which Branch Should You Use?

### 👉 The primary, active, consolidated branch is `main`.

If you are cloning, evaluating, or running Recall, **always use the `main` branch**:
```bash
git checkout main
```

### Why are there other branches?
During development, Recall was constructed following a strict, gated multi-phase protocol. The other branches in this repository:
- `feature/phase-0-foundation` through `feature/phase-7-frontend-auth`
- `fix/phase-7-security-contracts`
- `phase-8-release-readiness`

represent the **historical development milestones**. Each phase was formally frozen as an immutable Git tag (`phase-0-frozen` through `phase-7-frozen`). **All legitimate feature work, bug fixes, content expansion, and Tutor answer quality enhancements have been completely unified and consolidated into `main`**.

---

## 🏛 Core Architectural Invariants

Recall is engineered as a high-performance **Modular Monolith** governed by strict non-negotiable tenets:

1. **Zero Generative Scoring Authority ([ADR 0002](docs/adr/0002-deterministic-adaptive-learning-engine.md)):**  
   Language models are **never** permitted to grade student work, compute marks, or alter mastery states. All grading is computed deterministically by compiled Python algorithms implementing Armstrong's Axioms, Attribute Closure ($X^+$), Minimal Covers, and the Chase Matrix Lossless Join algorithm.
2. **Decoupled Bayesian Knowledge Tracing (BKT):**  
   Separates student Performance ($P \in [0, 1]$) from Evidence Confidence ($C \in [0, 1]$). Prevents catastrophic degradation—single careless mistakes trigger diagnostic exploration rather than destroying student mastery ranks.
3. **Collaborative SLM Verification Triad:**  
   AI cognition is separated into three distinct roles: **Generator (Role A: Tutor)**, **Evidence Reviewer (Role B)**, and **Adversarial Challenger (Role C)**, coordinated by a deterministic Verification Controller that strictly rejects simple majority voting.
4. **Server-Side Scored Assessment Lockout:**  
   When a student takes a scored exam or quiz, the backend automatically engages an HTTP 403 `AssessmentLockoutError`, preventing students from using the AI Tutor or Revisor to cheat.
5. **100% On-Device / Local Execution:**  
   Runs entirely on local hardware using quantized SLMs (`phi3:mini`) served via Ollama. Zero cloud API dependencies, zero token costs, and complete student privacy.

---

## 🚀 Step-by-Step Local Setup & Execution Guide

Follow these instructions to run the entire platform locally on your machine.

### Prerequisites
- **Git**
- **Python 3.12+**
- **Node.js 18+** & **npm**
- **Ollama** installed locally ([Download Ollama](https://ollama.ai))

---

### Step 1: Clone the Repository & Checkout `main`
```bash
git clone https://github.com/someshbharathwaj-ops/Genesis_Hackathon.git
cd Genesis_Hackathon
git checkout main
```

---

### Step 2: Pull the Local SLM & Embedding Models
Ensure the Ollama application is running on your system, then pull the required models:
```bash
# Pull the primary 3.8B Small Language Model
ollama pull phi3:mini

# Pull the vector embedding model for course syllabus search
ollama pull nomic-embed-text
```

---

### Step 3: Backend Setup (FastAPI & Engines)

1. Open a terminal and navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create and activate a Python virtual environment:
   ```bash
   # On Windows (PowerShell):
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1

   # On Linux/macOS:
   python -m venv .venv
   source .venv/bin/activate
   ```

3. Install backend dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```

4. Verify or create your environment configuration:
   The backend includes default fallback values. To explicitly configure your environment:
   ```bash
   # On Windows (PowerShell):
   Copy-Item ../.env.example .env

   # On Linux/macOS:
   cp ../.env.example .env
   ```

5. Seed the initial courses, syllabus materials, and question banks:
   ```bash
   python scripts/validate_and_ingest_content.py
   ```

6. Start the backend development server:
   ```bash
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

7. **Verify Backend Health:**  
   Open your browser and navigate to:
   - Health Probe: [http://127.0.0.1:8000/api/v1/healthz](http://127.0.0.1:8000/api/v1/healthz) (returns `{"status":"healthy"}`)
   - Interactive Swagger API Documentation: [http://127.0.0.1:8000/api/v1/docs](http://127.0.0.1:8000/api/v1/docs)

---

### Step 4: Frontend Setup (Next.js 15 Tactile UI)

1. Open a second terminal window and navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install frontend dependencies:
   ```bash
   npm install
   ```

3. Start the Next.js development server:
   ```bash
   npm run dev
   ```

4. Open your web browser at:
   👉 **[http://localhost:3000](http://localhost:3000)**

---

## 🎮 How to Test and Explore the Platform (Demo Personas)

Recall includes **1-Click Instant Demo Login** buttons on the navigation bar:

### 1. Student Persona — Ada Lovelace (`student.ada@recall.edu`)
- **Interactive Practice:** Solve database normalization and candidate key problems. Submitting an answer triggers deterministic algebraic grading with step-by-step point deductions and hint degradation.
- **Curriculum DAG:** View the interactive learning dependency graph across topics (`LO_CLOSURE` $\to$ `LO_KEYS` $\to$ `LO_NORMALIZATION`).
- **Grounded AI Tutor:** Ask complex academic questions (e.g., *"Is relation EMPLOYEE_DEPT in 3NF?"*). The Tutor responds with structured candidate key derivations, violation proofs, and verified slide citations (`[Lecture: Chapter10-normalization.pdf, Page 39]`).
- **Spaced Retention Scheduling:** View your personalized review queue governed by Ebbinghaus retention curves with a 1-hour working-memory cooldown.
- **Assessment Lockout:** Start an `independent_checkpoint` to observe the server-side HTTP 403 guard blocking tutor assistance during exams!

### 2. Instructor Persona — Prof. E. F. Codd (`instructor.dbms@recall.edu`)
- **Knowledge Base Ingestion:** Upload `.pdf`, `.docx`, `.pptx`, or `.md` lecture decks. The Knowledge Engine extracts text with SHA-256 deduplication and indexes vector chunks.
- **Schedule Assessments:** Schedule upcoming quizzes with dates and passing thresholds. Scheduled quizzes automatically notify enrolled students and render on their upcoming assessment calendars.

### 3. Administrator Persona — Audit Officer (`admin.audit@recall.edu`)
- **Audit Console:** Inspect immutable system logs, role authorization events, and multi-course seed controls.

---

## 🧪 Automated Test Verification

Recall maintains a **100% automated test pass rate** across all components:

```bash
cd backend

# Run all 108 backend unit tests (0.12s execution)
pytest tests/unit -v

# Run all 33 backend integration tests (role auth, scheduling, lockout)
pytest tests/integration -v

# Run frontend type checking & production compilation
cd ../frontend
npm run build
```

---

## 📜 Patent & Intellectual Property Notice

**Patent Pending — Intellectual Property Declaration**

Certain technological architectures, algorithms, and workflows implemented within this software repository are the subject of patent applications and proprietary rights owned by the inventors (**Somesh Bharathwaj, Nandina Ankers, Nishitha Gowri, and Niranjan Reddy**), including but not limited to:

1. **Deterministic Relational Grading Engine & Knowledge State Tracing:**  
   Systems and methods for automated, non-generative academic assessment evaluation utilizing fixpoint Armstrong closures, Chase tableau matrices, and Bayesian Knowledge Tracing with decoupled evidence-confidence metrics.
2. **Multi-Role Collaborative SLM Verification Pipeline:**  
   System and computer-implemented methods for bounded local language model execution utilizing role-differentiated generation (Tutor), evidence auditing (Reviewer), and adversarial probing (Challenger) arbitrated by a non-voting deterministic verification controller.
3. **Protocol-Level Server-Side Assessment Lockout State Machine:**  
   Security architectures for enforcing academic assessment lockouts against generative AI assistance at the API gateway layer via persistent attempt lifecycle state machines.

Unauthorized commercial replication of these patented methods without prior written license is strictly prohibited.

---

## 📄 License

This project is licensed under the **Apache License, Version 2.0**.

You may obtain a copy of the License in the [LICENSE](LICENSE) file or at:
[http://www.apache.org/licenses/LICENSE-2.0](http://www.apache.org/licenses/LICENSE-2.0)

Under the terms of the Apache 2.0 license:
- You are granted a worldwide, royalty-free license to use, reproduce, and prepare derivative works for academic, evaluation, and open-source purposes.
- Subject to the express grant of patent rights contained in Section 3 of the Apache License 2.0.

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
