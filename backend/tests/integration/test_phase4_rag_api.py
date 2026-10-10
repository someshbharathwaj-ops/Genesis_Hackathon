"""Integration tests for Phase 4: Document Ingestion and RAG APIs."""

import pytest
from httpx import AsyncClient


@pytest.mark.integration
async def test_phase4_document_ingestion_and_rag_lifecycle(async_client: AsyncClient) -> None:
    # 1. Seed courses
    seed_resp = await async_client.post("/api/v1/courses/seed/dbms")
    assert seed_resp.status_code == 201
    course_id = seed_resp.json()["course_id"]

    # Create a second course for tenant isolation testing
    course2_resp = await async_client.post(
        "/api/v1/courses",
        json={
            "code": "CS401",
            "title": "Advanced Operating Systems",
            "description": "OS Kernels and Distributed Systems",
        },
    )
    assert course2_resp.status_code == 201
    course2_id = course2_resp.json()["id"]

    # 2. Upload and ingest course document for CS340
    doc_text = (
        "Course Lecture 1: Relational Database Systems.\n\n"
        "Functional dependencies (FDs) represent semantic integrity constraints. "
        "A functional dependency X -> Y holds on relation R if tuples agreeing on X "
        "also agree on Y.\n\n"
        "Armstrong's Axioms provide a sound and complete inference system:\n"
        "1. Reflexivity: If Y is a subset of X, then X -> Y.\n"
        "2. Augmentation: If X -> Y, then XZ -> YZ.\n"
        "3. Transitivity: If X -> Y and Y -> Z, then X -> Z.\n\n"
        "Attribute Closure X+ is the set of all attributes functionally determined by X."
    )
    upload_resp = await async_client.post(
        f"/api/v1/courses/{course_id}/documents/upload",
        files={"file": ("dbms_lecture1.txt", doc_text.encode("utf-8"), "text/plain")},
    )
    assert upload_resp.status_code == 201
    doc_data = upload_resp.json()
    assert doc_data["status"] == "indexed"
    assert doc_data["chunk_count"] >= 1
    doc_id = doc_data["id"]

    # 3. Repeat-safe idempotency test: uploading same document again does not duplicate
    reupload_resp = await async_client.post(
        f"/api/v1/courses/{course_id}/documents/upload",
        files={"file": ("dbms_lecture1.txt", doc_text.encode("utf-8"), "text/plain")},
    )
    assert reupload_resp.status_code == 201
    reupload_data = reupload_resp.json()
    assert reupload_data["id"] == doc_id
    assert reupload_data["chunk_count"] == doc_data["chunk_count"]

    # Verify document list count remains 1
    list_docs_resp = await async_client.get(f"/api/v1/courses/{course_id}/documents")
    assert list_docs_resp.status_code == 200
    docs_list = list_docs_resp.json()
    assert len(docs_list) == 1

    # 4. Ingest document for second course (CS401)
    os_doc_text = (
        "Operating Systems: Virtual memory, page replacement algorithms, and kernel semaphores."
    )
    upload_course2_resp = await async_client.post(
        f"/api/v1/courses/{course2_id}/documents/upload",
        files={"file": ("os_lecture1.txt", os_doc_text.encode("utf-8"), "text/plain")},
    )
    assert upload_course2_resp.status_code == 201
    assert upload_course2_resp.json()["id"] is not None

    # 5. Course-isolated semantic retrieval
    # Query CS340 for functional dependencies
    retrieval_resp = await async_client.post(
        f"/api/v1/courses/{course_id}/knowledge/retrieve",
        json={"query": "What are Armstrong's axioms and transitivity?", "top_k": 3},
    )
    assert retrieval_resp.status_code == 200
    ret_data = retrieval_resp.json()
    assert not ret_data["abstention_recommended"]
    assert len(ret_data["matches"]) > 0

    first_match = ret_data["matches"][0]
    assert "Armstrong" in first_match["content"] or "Transitivity" in first_match["content"]
    assert "[Lecture: dbms_lecture1.txt, Page 1]" in first_match["citation"]

    # Strict isolation check: OS content must NEVER appear in CS340 retrieval
    assert all("Operating Systems" not in m["content"] for m in ret_data["matches"])

    # Query CS401 for operating systems
    os_retrieval_resp = await async_client.post(
        f"/api/v1/courses/{course2_id}/knowledge/retrieve",
        json={"query": "Virtual memory and page replacement", "top_k": 3},
    )
    assert os_retrieval_resp.status_code == 200
    os_ret_data = os_retrieval_resp.json()
    assert not os_ret_data["abstention_recommended"]
    assert len(os_ret_data["matches"]) > 0
    # DBMS lecture must NEVER appear in CS401
    assert all("Armstrong" not in m["content"] for m in os_ret_data["matches"])

    # 6. Honest abstention test: query completely irrelevant to curriculum
    irrelevant_resp = await async_client.post(
        f"/api/v1/courses/{course_id}/knowledge/retrieve",
        json={
            "query": "Mitochondria cellular respiration in eukaryotic cells",
            "similarity_threshold": 0.60,
        },
    )
    assert irrelevant_resp.status_code == 200
    irrel_data = irrelevant_resp.json()
    assert irrel_data["abstention_recommended"]
    assert len(irrel_data["matches"]) == 0
    assert "recommends abstaining" in irrel_data["explanation"]

    # 7. Document detail endpoint
    detail_resp = await async_client.get(
        f"/api/v1/courses/{course_id}/documents/{doc_id}"
    )
    assert detail_resp.status_code == 200
    detail_data = detail_resp.json()
    assert len(detail_data["chunks"]) > 0
    assert detail_data["chunks"][0]["page_number"] == 1

    # 8. Malformed and edge case error handling
    # Corrupt PDF
    bad_pdf_resp = await async_client.post(
        f"/api/v1/courses/{course_id}/documents/upload",
        files={"file": ("corrupt.pdf", b"%PDF-corrupt-data-not-a-real-pdf", "application/pdf")},
    )
    assert bad_pdf_resp.status_code == 422
    assert bad_pdf_resp.json()["code"] == "DOCUMENT_EXTRACTION_ERROR"

    # Unsupported file format
    unsupported_resp = await async_client.post(
        f"/api/v1/courses/{course_id}/documents/upload",
        files={"file": ("archive.zip", b"PK\x03\x04...", "application/zip")},
    )
    assert unsupported_resp.status_code == 415
    assert unsupported_resp.json()["code"] == "UNSUPPORTED_DOCUMENT_FORMAT"

    # 9. Delete document
    del_resp = await async_client.delete(f"/api/v1/courses/{course_id}/documents/{doc_id}")
    assert del_resp.status_code == 204

    # Verification: document list is now empty
    empty_list_resp = await async_client.get(f"/api/v1/courses/{course_id}/documents")
    assert empty_list_resp.status_code == 200
    assert len(empty_list_resp.json()) == 0
