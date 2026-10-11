# Recall — Comprehensive Question Bank, Knowledge Base & Learning DAG Expansion Specification

**Document Version:** 1.0.0  
**Status:** Approved & Active Architecture Standard  
**Target Platform:** Recall Institutional AI Mentor  
**Scope:** Every registered course in Recall (`CS340: Database Management Systems`, `CS301: Operating Systems & Concurrency`, `CS305: Computer Networks & Internet Protocols`)  

---

## 1. Executive Summary & Problem Statement

Recall employs an authoritative Bayesian knowledge tracing and bounded diagnostic session planner (`BoundedDiagnosisEngine` and `MasteryEngine`). By institutional design, the platform enforces a **five-question ceiling per diagnostic session** (`MAX_DIAGNOSTIC_SESSION_QUESTIONS = 5`) to prevent cognitive exhaustion, preserve measurement validity, and avoid assessing transient working-memory recall.

However, an institutional diagnostic platform requires an extensive, deep, and multi-tier underlying inventory of validated questions, granular learning objectives, and grounded knowledge passages. A diagnostic session may be bounded to 5 targeted probes, but the underlying question bank must contain hundreds of unique, deterministic, curriculum-aligned items across diverse cognitive levels and topics.

This specification details the end-to-end architecture for expanding Recall's real question bank, course-grounded Markdown knowledge base, prerequisite-directed acyclic graph (learning DAG), and retrieval-grounded AI Tutor answer reliability across all registered courses without mutating frozen Git milestone tags (`phase-0-frozen` through `phase-7-frozen`) or breaking existing persistence.

---

## 2. Mandatory Repository Discovery & Course Inventory

### 2.1 Canonical Course Registry

| Course Code | Canonical Course ID | Full Course Title | Core Domain & Focus | Source Material Inventory | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **CS340** | `1651bee3-3875-4014-b335-dd38caea2622` | Database Management Systems | Relational Model, Functional Dependencies, Normalization, SQL, Transactions & 2PL | 23 source files in `DBMS/theory/` (Silberschatz text, lecture slides, decomposition notes) | **Fully Sourced** |
| **CS301** | `582c2678-1f15-482f-bf49-49dd2e711584` | Operating Systems & Concurrency | Processes, Threads, CPU Scheduling, Synchronization, Semaphores, Deadlocks, Paging | 13 source files in `OS/theory/` (Lecture slide decks, synchronization programs, practice notes) | **Fully Sourced** |
| **CS305** | `8fb75ef3-5c18-411b-8a92-fbae38926ab0` | Computer Networks & Internet Protocols | Layered Architecture, Physical & Data Link, Transport (TCP/UDP), Congestion Control, Routing | Syllabus registered in SQLite; core lecture units identified | **Syllabus Mapped** |

### 2.2 Active Services and Integration Contracts
- **Curriculum & Topics:** [curriculum_service.py](file:///c:/Users/SOMESH%20BHARATHWAJ/Documents/AIML/projects/Genesis_Hackathon/Genesis_Hackathon/backend/app/services/curriculum_service.py), [curriculum.py](file:///c:/Users/SOMESH%20BHARATHWAJ/Documents/AIML/projects/Genesis_Hackathon/Genesis_Hackathon/backend/app/models/curriculum.py)
- **Question Repository:** [question_repo.py](file:///c:/Users/SOMESH%20BHARATHWAJ/Documents/AIML/projects/Genesis_Hackathon/Genesis_Hackathon/backend/app/repositories/question_repo.py), [question.py](file:///c:/Users/SOMESH%20BHARATHWAJ/Documents/AIML/projects/Genesis_Hackathon/Genesis_Hackathon/backend/app/models/question.py)
- **Deterministic Evaluation & Attempts:** [attempt_service.py](file:///c:/Users/SOMESH%20BHARATHWAJ/Documents/AIML/projects/Genesis_Hackathon/Genesis_Hackathon/backend/app/services/attempt_service.py), [dbms_grader.py](file:///c:/Users/SOMESH%20BHARATHWAJ/Documents/AIML/projects/Genesis_Hackathon/Genesis_Hackathon/backend/app/modules/adaptive_learning/dbms_grader.py)
- **Mastery Estimation (BKT):** [mastery_engine.py](file:///c:/Users/SOMESH%20BHARATHWAJ/Documents/AIML/projects/Genesis_Hackathon/Genesis_Hackathon/backend/app/modules/adaptive_learning/mastery_engine.py)
- **Bounded Diagnostic Probing:** [diagnosis_engine.py](file:///c:/Users/SOMESH%20BHARATHWAJ/Documents/AIML/projects/Genesis_Hackathon/Genesis_Hackathon/backend/app/modules/adaptive_learning/diagnosis_engine.py), [diagnosis_service.py](file:///c:/Users/SOMESH%20BHARATHWAJ/Documents/AIML/projects/Genesis_Hackathon/Genesis_Hackathon/backend/app/services/diagnosis_service.py)
- **Spaced Retention Scheduling:** [scheduling_engine.py](file:///c:/Users/SOMESH%20BHARATHWAJ/Documents/AIML/projects/Genesis_Hackathon/Genesis_Hackathon/backend/app/modules/adaptive_learning/scheduling_engine.py)
- **Knowledge RAG Engine:** [knowledge_service.py](file:///c:/Users/SOMESH%20BHARATHWAJ/Documents/AIML/projects/Genesis_Hackathon/Genesis_Hackathon/backend/app/services/knowledge_service.py), [retrieval_engine.py](file:///c:/Users/SOMESH%20BHARATHWAJ/Documents/AIML/projects/Genesis_Hackathon/Genesis_Hackathon/backend/app/modules/knowledge_engine/retrieval_engine.py)
- **Grounded Tutor Engine:** [tutor_engine.py](file:///c:/Users/SOMESH%20BHARATHWAJ/Documents/AIML/projects/Genesis_Hackathon/Genesis_Hackathon/backend/app/modules/ai_engine/tutor_engine.py), [tutor_service.py](file:///c:/Users/SOMESH%20BHARATHWAJ/Documents/AIML/projects/Genesis_Hackathon/Genesis_Hackathon/backend/app/services/tutor_service.py)

---

## 3. Target Three-Tier Content Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                        TIER 1: LEARNING DAG                            │
│  Topic Nodes ──► Granular Learning Objectives ──► Prerequisite Edges  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Links To
          ┌─────────────────────────┴─────────────────────────┐
          ▼                                                   ▼
┌───────────────────────────────────┐   ┌────────────────────────────────┐
│   TIER 2: QUESTION BANK LEDGER    │   │  TIER 3: KNOWLEDGE BASE (RAG)  │
│ - Deterministic Question Schemas  │   │ - Granular Markdown Modules    │
│ - Provenance Hashes & Rubrics     │   │ - Definitions & Step Traces    │
│ - Difficulty & Misconception Tags │   │ - Real Lecture Source Citations│
└───────────────────────────────────┘   └────────────────────────────────┘
```

### Layer A: The Question Bank
- **Model Standard:** Inherits from `Question` and `QuestionVersion` with strict schema validation.
- **Attributes:**
  - `id`: Stable UUIDv4.
  - `course_id`: Foreign key to `Course.id`.
  - `topic_id`: Foreign key to `Topic.id`.
  - `objective_id`: Foreign key to `LearningObjective.id`.
  - `question_type`: `MULTIPLE_CHOICE`, `MULTIPLE_SELECT`, `EXPRESSION`, `NUMERICAL`, `TEXT`, `MINIMAL_COVER`, `DECOMPOSITION`.
  - `difficulty`: `DifficultyLevel.INTRODUCTORY` (Easy), `DifficultyLevel.INTERMEDIATE` (Medium), `DifficultyLevel.ADVANCED` (Hard).
  - `prompt`: Precise problem statement with domain notation.
  - `answer_key`: Structured JSON dict (e.g. `{"closure": "A, B, C", "correct_options": ["B", "D"]}`).
  - `rubric`: Deterministic scoring rules and partial credit breakdown.
  - `explanation`: Comprehensive solution derivation.
  - `provenance_hash`: SHA-256 cryptographic digest over prompt + answer_key + rubric.
  - `verification_status`: `VerificationStatus.VERIFIED`.

### Layer B: Modular Markdown Knowledge Base
Organized per course into focused conceptual markdown files under `knowledge/<course_code>/`:
```text
knowledge/
├── CS340/
│   ├── dbms_relational_algebra.md
│   ├── dbms_sql_queries_and_constraints.md
│   ├── dbms_functional_dependencies.md
│   ├── dbms_normalization_and_decomposition.md
│   └── dbms_transactions_concurrency.md
├── CS301/
│   ├── os_process_lifecycle_and_threads.md
│   ├── os_concurrency_and_scheduling.md
│   ├── os_synchronization_and_semaphores.md
│   ├── os_deadlocks_and_resource_allocation.md
│   └── os_memory_paging_and_virtual_memory.md
└── CS305/
    ├── cn_layered_architecture_and_osi.md
    ├── cn_transport_layer_tcp_udp.md
    └── cn_network_routing_and_ip.md
```

Each Markdown knowledge document provides:
1. `course_code` and `topic_code` frontmatter headers.
2. Formal mathematical/procedural definitions.
3. Axioms, theorems, and state machine rules.
4. Step-by-step worked traces.
5. Common student misconceptions with corrective explanations.
6. Exact citations pointing to university textbook chapters and lecture slide decks.

### Layer C: The Learning-Objective DAG
The curriculum is represented as a directed acyclic graph $G = (V, E)$, where vertices $V$ are `LearningObjective` nodes and directed edges $(u, v) \in E$ indicate that objective $u$ is an authoritative prerequisite for objective $v$.
- **DAG Invariants:**
  1. $\forall (u, v) \in E, \text{course}(u) = \text{course}(v)$ (intra-course prerequisite isolation).
  2. $G$ contains **zero directed cycles** ($\text{Cycle}(G) = \emptyset$).
  3. Every root objective ($\text{in-degree}(v) = 0$) represents foundational introductory knowledge.
  4. Topologically sorted execution guarantees prerequisite satisfaction before advanced synthesis.

---

## 4. Question Bank Expansion Targets & Distribution

| Metric / Dimension | Target Specification |
| :--- | :--- |
| **Questions Per Objective** | 15–30 verified questions per major learning objective |
| **Difficulty Distribution** | $\ge 5$ Introductory (Easy), $\ge 5$ Intermediate (Medium), $\ge 3$ Advanced (Hard) |
| **Question Type Diversity** | Expression (30%), Multiple Choice (30%), Multi-Select (20%), Analytical/Trace (20%) |
| **Provenance Integrity** | 100% of questions verified with SHA-256 provenance hashes |
| **Grading Determinism** | 100% of scored questions evaluated via deterministic rubrics without LLM drift |
| **Citation Grounding** | 100% of knowledge files tagged with lecture provenance references |

---

## 5. Prerequisite Learning DAG Validation Specification

### 5.1 Formal Topological Sorting Algorithm
Validation must run Kahn’s algorithm or depth-first search cycle detection over every registered course's objective graph before content ingestion:

```python
def validate_curriculum_dag(objectives: list[LearningObjective]) -> list[str]:
    in_degree = {obj.id: 0 for obj in objectives}
    adj = {obj.id: [] for obj in objectives}
    obj_ids = set(in_degree.keys())

    for obj in objectives:
        for prereq_id in obj.prerequisite_objective_ids:
            if prereq_id not in obj_ids:
                raise ValidationError(f"Dangling prerequisite reference: {prereq_id}")
            adj[prereq_id].append(obj.id)
            in_degree[obj.id] += 1

    queue = [o_id for o_id, deg in in_degree.items() if deg == 0]
    visited_count = 0

    while queue:
        curr = queue.pop(0)
        visited_count += 1
        for nxt in adj[curr]:
            in_degree[nxt] -= 1
            if in_degree[nxt] == 0:
                queue.append(nxt)

    if visited_count != len(objectives):
        raise CyclicDependencyError("Curriculum DAG contains a directed cycle!")
```

---

## 6. Deterministic Grading Engine Standards

All student answers submitted to the expanded question bank are graded by deterministic evaluators implementing frozen architectural decision rules (**ADR 0001: Deterministic Mathematical Grading**):

1. **Attribute Closure Evaluator:** Normalizes comma/whitespace separated sets and validates that $\{X\}^+$ contains all and only closure attributes derived under Armstrong axioms.
2. **Candidate Key Evaluator:** Validates superkey property and minimality (no proper subset is a superkey).
3. **Multiple Choice & Multi-Select:** Exact key matching with penalty deductions for false-positive selections.
4. **Relational Algebra & SQL Expression Evaluator:** Canonical syntax tokenization and algebraic equivalency verification.
5. **CPU Scheduling & Concurrency Grader:** Quantitative verification of Gantt chart intervals, turnaround times, and semaphore wait/signal sequences.

---

## 7. Tutor Answer Quality, Structure & Reliability Enhancement (Section 13)

### 7.1 The First-Attempt Quality Standard
Tutor generation must produce structured, accurate, course-grounded responses on the **very first student query**, eliminating repeated manual reruns, truncated responses, and ungrounded hallucinations.

### 7.2 The 7-Section Pedagogical Response Contract
For conceptual and analytical queries, the Tutor engine formats output into structured Markdown:

1. **📌 Direct Answer:** A concise, unequivocal 1-sentence answer answering the prompt immediately.
2. **🔍 Core Concept:** Clear definition grounded in official course syllabus notes.
3. **⚙️ Step-by-Step Breakdown:** Procedural reasoning, formula application, or algorithm trace.
4. **💡 Concrete Worked Example:** Small, illustrative problem with input, intermediate step, and verified output.
5. **⚠️ Common Misconception:** Specific conceptual trap to avoid during examinations.
6. **📝 Essential Takeaway:** Memorable summary bullet point for revision.
7. **📚 Authoritative Citations:** Bracketed citations formatted as `[Lecture: <filename>, Page <X>]` pointing directly to ingested course documents.

### 7.3 Grounded Abstention Policy
If retrieved vector chunks have insufficient similarity ($\text{score} < 0.26$) or the query falls outside course scope, the Tutor emits the authoritative abstention:
> *"I could not find sufficient information in the official course materials for this course to answer your question. In accordance with Recall's grounding policy, I am abstaining from answering to prevent hallucination."*

---

## 8. Quality Gates & Acceptance Matrix

```text
========================================================================
QUALITY GATE CRITERIA                                           STATUS
========================================================================
[1] 100% of registered courses present in inventory           PASS
[2] Learning DAG cycle count == 0 across all courses          PASS
[3] No dangling prerequisite references in database           PASS
[4] Ingestion idempotency: duplicate runs produce 0 duplicates PASS
[5] Provenance hashes cryptographically verifiable             PASS
[6] Bounded diagnostic ceiling (<= 5 questions) preserved     PASS
[7] Scored assessment exam lockout (ADR 0002) intact          PASS
[8] Frozen tags (phase-0-frozen .. phase-7-frozen) intact     PASS
========================================================================
```
