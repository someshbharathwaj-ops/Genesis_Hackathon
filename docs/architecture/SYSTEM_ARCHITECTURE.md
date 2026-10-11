# Recall: System Architecture Specification

> **Canonical Document Reference:** For the complete in-depth architectural narrative, engine definitions, and mathematical models, refer to [ARCHITECTURE.md](file:///c:/Users/SOMESH%20BHARATHWAJ/Documents/AIML/projects/Genesis_Hackathon/Genesis_Hackathon/docs/architecture/ARCHITECTURE.md).

## 1. High-Level Modular Monolith Topology

Recall is architectured as an institutional-grade adaptive learning platform combining deterministic pedagogical intelligence with bounded local SLM execution.

```mermaid
graph TD
    Client([Next.js 15 Tactile Frontend]) -->|RFC 7807 REST / Bearer JWT| Gateway[FastAPI v1 Application Gateway]
    
    subgraph "Modular Monolith Core (backend/app)"
        Gateway --> ALE[Adaptive Learning Engine]
        Gateway --> KE[Knowledge Engine]
        Gateway --> AEE[AI Execution Engine]
        Gateway --> SEC[Security & Identity Context]
        
        ALE --> |Mastery, BKT, DAG Prereqs| RelationalDB[(SQLite / PostgreSQL)]
        KE --> |Course Syllabus Ingestion & Chunks| VectorStore[(Dense Vector Store / SQLite FTS)]
        
        ALE --> |Assessment Lockout / Rules| AEE
        KE --> |Syllabus Excerpts & Provenance| AEE
    end
    
    subgraph "Local SLM Inference"
        AEE --> |Role A: Tutor / Role B: Revisor| Ollama[Ollama SLM: phi3:mini]
    end
```

## 2. Engine Responsibilities

| Engine | Primary Responsibilities | Core Invariants |
| :--- | :--- | :--- |
| **Adaptive Learning Engine (ALE)** | Curriculum DAG, versioned question bank, deterministic DBMS grader, BKT mastery engine, bounded diagnostic sessions ($\le 5$ items), spaced retention review queue. | **Zero Generative Scoring:** All grading and mastery progression is computed by deterministic algorithms (ADR 0002). |
| **Knowledge Engine (KE)** | Repeat-safe lecture ingestion (PDF, DOCX, PPTX, TXT, MD), page-provenance chunking, course-isolated vector retrieval sandbox. | **Tenant Isolation & Provenance:** Chunks never cross course boundaries; citations retain exact page and filename metadata. |
| **AI Execution Engine (AEE)** | Grounded AI Tutor (Role A) and Grounded Revisor (Role B) SLM adapters, prompt assemblers, and output sanitizers. | **Assessment Lockout:** Scored assessment checkpoints disable tutor and revisor access (`403 AssessmentLockoutError`). Strict abstention when evidence is insufficient. |
| **Security & Identity** | RFC 7807 error modeling, Bearer JWT authentication, role-based access control (`student`, `instructor`, `admin`), student ownership verification. | **Zero Client Trust:** Student ID in route bodies is verified against token claims; instructors/admins cannot be impersonated. |

## 3. Architectural Decision Records (ADRs)

- [ADR 0001: Modular Monolith Architecture](file:///c:/Users/SOMESH%20BHARATHWAJ/Documents/AIML/projects/Genesis_Hackathon/Genesis_Hackathon/docs/adr/0001-modular-monolith-architecture.md)
- [ADR 0002: Deterministic Adaptive Learning Engine](file:///c:/Users/SOMESH%20BHARATHWAJ/Documents/AIML/projects/Genesis_Hackathon/Genesis_Hackathon/docs/adr/0002-deterministic-adaptive-learning-engine.md)
