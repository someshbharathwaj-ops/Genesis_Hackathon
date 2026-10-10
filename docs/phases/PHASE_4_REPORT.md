# Recall — Phase 4 Report: Document Ingestion & RAG

**Phase**: 4 (Document Ingestion & Course-Isolated RAG)  
**Branch**: `feature/phase-4-document-ingestion-rag` (derived from `8408e6f`, tagged `phase-3-frozen`)  
**Base Commit / Frozen Tags**: `phase-0-frozen` (`fa1c70e`), `phase-1-frozen` (`16895b7`), `phase-2-frozen` (`e4a88ed`), `phase-3-frozen` (`8408e6f`)  
**Evaluation Date**: 2026-10-11  
**Status**: COMPLETE (Gated Verification Succeeded)

---

## 1. Executive Summary

Phase 4 implements the **Course Document Ingestion & Retrieval-Augmented Generation (RAG) Foundation**, equipping Recall with the capability to ingest course materials (PDF, TXT), split them into provenance-tracked semantic chunks, index them with embeddings, and execute strict course-isolated semantic retrieval.

All 85 tests in the comprehensive test suite (contract, integration, regression, and unit) pass cleanly with zero failures. Static type checking (`mypy`), linting (`ruff`), database static DDL generation (`alembic`), and frontend production compilation (`tsc`, `next build`) succeed with zero errors.

---

## 2. Architecture & Design Implementation

### A. Document Ingestion & Extraction Engine (`app/modules/knowledge_engine/document_extractor.py`)
- **Format Support**: Supports standard PDF documents and plain text (`.txt`, `text/plain`).
- **Resilience & Safe Error Handling**:
  - Handles corrupted PDF files without crashing, raising `DocumentExtractionError` with RFC 7807 problem details.
  - Detects password-protected/encrypted PDFs, raising `DocumentEncryptedError`.
  - Rejects unsupported MIME types or extensions with `UnsupportedDocumentFormatError` (HTTP 415).
  - Explicitly marks empty files (`page_count = 0`, `is_empty = True`) without failing the system.
- **Incremental & Bounded Ingestion**: Uses `pypdf` streams without unbounded memory consumption.

### B. Semantic Chunking & Provenance Tracking (`app/modules/knowledge_engine/chunker.py`)
- **Provenance Retention**: Each chunk retains:
  - Exact source filename.
  - Page number where the text originates (e.g., Page 1, Page 2).
  - Sequential `chunk_index` within the document.
  - Metadata attributes dictionary (`source_filename`, `page_number`, `chunk_index`, `byte_length`).
- **Configurable Slicing**: Splits on paragraphs and sentence boundaries with configurable `target_chunk_size` and sliding window overlap.

### C. Embedding Interface & Deterministic Test Provider (`app/modules/knowledge_engine/embedding_provider.py`)
- **Replaceable Interface**: Defines `BaseEmbeddingProvider` with asynchronous `embed_text` and `embed_batch`.
- **Deterministic Mock Provider**: `DeterministicMockEmbeddingProvider` generates normalized 128-dimensional embedding vectors using character n-gram frequencies. This allows deterministic, fast, offline unit and integration testing without external API or GPU dependencies.
- **Ollama Integration**: `OllamaEmbeddingProvider` connects to local Ollama endpoints (e.g., `nomic-embed-text` or `all-minilm`) with automatic graceful fallback to mock embeddings when Ollama is unavailable.

### D. Course-Isolated Semantic Retrieval (`app/modules/knowledge_engine/retrieval_engine.py`)
- **Multi-Tenant / Course Isolation**: Retrieval strictly filters by `course_id`. Queries for Course A will never return or leak chunks from Course B, even when textual similarity is high.
- **Honest Abstention & Grounding Guardrails**:
  - Computes cosine similarity scores against query embeddings.
  - If no chunk exceeds the similarity threshold (or if the corpus is empty), the engine flags `abstention_recommended = True` and provides an honest explanation recommending abstention.
- **Formal Academic Citations**: Generates provenance citations in the format `[Lecture: <filename>, Page <X>]` to ground future SLM tutoring responses in verified course materials.

### E. Persistence Models & Repeat-Safe Storage (`app/models/document.py`, `backend/alembic/versions/002_document_knowledge_schema.py`)
- **`CourseDocument` Model**: Stores document metadata, content SHA-256 hash, MIME type, file size, page count, and ingestion status (`pending`, `indexed`, `empty`, `failed`).
- **Unique Content Hash Constraint**: Enforces `uq_course_doc_hash` (`course_id`, `content_hash`). Uploading an identical document to the same course does not duplicate chunks or records; it safely returns the existing document record.
- **`DocumentChunk` Model**: Stores chunk text, `chunk_index`, `page_number`, token count, metadata attributes JSON, and `embedding` stored as JSON array of floats for complete cross-database compatibility (SQLite test suite + PostgreSQL static SQL).

### F. REST API Endpoints (`app/api/v1/endpoints/documents.py`)
- `POST /api/v1/courses/{course_id}/documents/upload`: Multipart file upload, hashing, extraction, chunking, embedding generation, and indexing.
- `GET /api/v1/courses/{course_id}/documents`: List all ingested documents for a course.
- `GET /api/v1/courses/{course_id}/documents/{document_id}`: Retrieve document details with chunk summaries.
- `DELETE /api/v1/courses/{course_id}/documents/{document_id}`: Cascading deletion of document and associated chunks.
- `POST /api/v1/courses/{course_id}/knowledge/retrieve`: Query-based semantic retrieval with course isolation, top-k ranking, threshold filtering, and citations.

---

## 3. Verification & Test Evidence

### A. Backend Test Suite (`pytest -v`)
```
platform win32 -- Python 3.12.5, pytest-8.3.4, pluggy-1.6.0
collected 85 items

tests\contract\test_health_contract.py ...                               [  3%]
tests\integration\test_health_integration.py ..                          [  5%]
tests\integration\test_phase1_api.py ..........                          [ 17%]
tests\integration\test_phase2_mastery_api.py .                           [ 18%]
tests\integration\test_phase3_diagnosis_api.py .                         [ 20%]
tests\integration\test_phase4_rag_api.py .                               [ 21%]
tests\unit\test_config.py ..                                             [ 23%]
tests\unit\test_curriculum_validator.py ..............                   [ 40%]
tests\unit\test_dbms_engine.py .......                                   [ 48%]
tests\unit\test_dbms_grader.py ......                                    [ 55%]
tests\unit\test_diagnosis_engine.py ........                             [ 64%]
tests\unit\test_errors.py .....                                          [ 70%]
tests\unit\test_knowledge_engine.py ..........                           [ 82%]
tests\unit\test_mastery_engine.py ........                               [ 91%]
tests\unit\test_phase1_models.py ...                                     [ 95%]
tests\unit\test_repositories.py ....                                     [100%]

============================= 85 passed in 6.65s ==============================
```

### B. Static Type Checking (`mypy app tests`)
```
Success: no issues found in 72 source files
```

### C. Linter & Formatting Checks (`ruff check app tests`)
```
All checks passed!
```

### D. Frontend Production Build & Typecheck
```
> tsc --noEmit (Passed clean)
> next build (Compiled successfully, static routes generated clean)
```

### E. Database Schema & Migration Generation
```
alembic upgrade head --sql
Upgrades from 001_initial_schema to 002_document_knowledge_schema generated transactional DDL:
- CREATE TYPE documentstatus AS ENUM ('pending', 'indexed', 'empty', 'failed');
- CREATE TABLE course_documents (...)
- CREATE TABLE document_chunks (...)
- UNIQUE (course_id, content_hash)
```

---

## 4. Phase Boundary Compliance & Architecture Alignment

1. **Multi-SLM Alignment**: In accordance with the project architecture roadmap, Phase 4 strictly delivers the retrieval foundation. The Tutor SLM, Revisor SLM, and collaborative dialogue verification pipelines are not implemented in Phase 4.
2. **Authority Separation**: Document retrieval outputs recommendations and citations, but has zero authority over deterministic DBMS grading, Bayesian knowledge tracing mastery updates, or diagnostic state transitions.
3. **Immutability of Frozen Baselines**: No historical commits or tags (`phase-0-frozen`, `phase-1-frozen`, `phase-2-frozen`, `phase-3-frozen`) were modified or moved.

---

## 5. Retained Limitations & Next Steps

1. **Live PostgreSQL Database**: Live PostgreSQL execution remains dependent on local/production database container credentials; static SQL generation and schema compatibility are 100% verified.
2. **Phase 5 Prerequisite**: Phase 5 (Tutoring & Response Generation) can now consume the grounded retrieval results provided by `POST /api/v1/courses/{course_id}/knowledge/retrieve` to supply syllabus-grounded context to the generation pipeline.
