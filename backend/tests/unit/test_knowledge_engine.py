"""Unit tests for Knowledge Engine: extraction, chunking, embeddings, and retrieval."""

import io

import pypdf
import pytest

from app.core.errors import (
    DocumentEncryptedError,
    DocumentExtractionError,
    UnsupportedDocumentFormatError,
)
from app.models.document import DocumentChunk
from app.modules.knowledge_engine.chunker import SemanticChunker
from app.modules.knowledge_engine.document_extractor import DocumentExtractor
from app.modules.knowledge_engine.embedding_provider import DeterministicMockEmbeddingProvider
from app.modules.knowledge_engine.retrieval_engine import (
    KnowledgeRetrievalEngine,
    compute_cosine_similarity,
)


def _create_simple_blank_pdf(num_pages: int = 1) -> bytes:
    """Generate in-memory PDF bytes with blank pages."""
    writer = pypdf.PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=612, height=792)
    stream = io.BytesIO()
    writer.write(stream)
    return stream.getvalue()


@pytest.mark.unit
def test_pdf_extraction_blank_pages() -> None:
    pdf_bytes = _create_simple_blank_pdf(2)
    res = DocumentExtractor.extract_from_bytes(
        file_bytes=pdf_bytes,
        filename="blank.pdf",
    )
    assert res.is_empty
    assert res.page_count == 2


@pytest.mark.unit
def test_txt_extraction_valid() -> None:
    text_content = "Relational DBMS. Functional Dependencies and Armstrong Axioms."
    res = DocumentExtractor.extract_from_bytes(
        file_bytes=text_content.encode("utf-8"),
        filename="lecture1.txt",
    )
    assert not res.is_empty
    assert res.page_count == 1
    assert len(res.text_by_page) == 1
    assert "Armstrong Axioms" in res.text_by_page[0][1]


@pytest.mark.unit
def test_empty_document_detection() -> None:
    res = DocumentExtractor.extract_from_bytes(
        file_bytes=b"",
        filename="empty.txt",
    )
    assert res.is_empty
    assert res.page_count == 0


@pytest.mark.unit
def test_unsupported_document_format() -> None:
    with pytest.raises(UnsupportedDocumentFormatError):
        DocumentExtractor.extract_from_bytes(
            file_bytes=b"GIF89a...",
            filename="image.gif",
        )


@pytest.mark.unit
def test_corrupted_pdf_handling() -> None:
    corrupted_bytes = b"%PDF-1.4 this is a corrupt header with invalid xref table\x00\xff"
    with pytest.raises(DocumentExtractionError):
        DocumentExtractor.extract_from_bytes(
            file_bytes=corrupted_bytes,
            filename="corrupt.pdf",
        )


@pytest.mark.unit
def test_encrypted_pdf_handling() -> None:
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.encrypt("secret_password")
    stream = io.BytesIO()
    writer.write(stream)
    enc_bytes = stream.getvalue()

    with pytest.raises(DocumentEncryptedError):
        DocumentExtractor.extract_from_bytes(
            file_bytes=enc_bytes,
            filename="encrypted.pdf",
        )


@pytest.mark.unit
def test_semantic_chunker_provenance() -> None:
    text_pages = [
        (1, "Page 1: Functional dependencies define constraints on relations. A -> B."),
        (2, "Page 2: Armstrong Axioms include Reflexivity, Augmentation, and Transitivity."),
    ]
    chunks = SemanticChunker.chunk_document(
        text_by_page=text_pages,
        filename="cs340_notes.pdf",
        target_chunk_size=100,
        overlap=20,
    )

    assert len(chunks) >= 2
    # Check page numbers are preserved
    assert chunks[0].page_number == 1
    assert chunks[0].metadata_attributes["source_filename"] == "cs340_notes.pdf"
    assert any(c.page_number == 2 for c in chunks)


@pytest.mark.unit
def test_deterministic_mock_embeddings_similarity() -> None:
    provider = DeterministicMockEmbeddingProvider()
    vec1 = provider._generate_vector("Functional dependency attribute closure computation")
    vec2 = provider._generate_vector("Attribute closure derivation under functional dependencies")
    vec3 = provider._generate_vector("Quantum mechanics entanglement Schrödinger equation wave")

    assert len(vec1) == 128
    sim_related = compute_cosine_similarity(vec1, vec2)
    sim_unrelated = compute_cosine_similarity(vec1, vec3)

    # Domain-related texts sharing vocabulary have higher similarity than unrelated text
    assert sim_related > sim_unrelated
    assert sim_related > 0.40


@pytest.mark.unit
def test_course_isolated_retrieval() -> None:
    provider = DeterministicMockEmbeddingProvider()
    q_vec = provider._generate_vector("Functional dependencies in relational databases")

    chunk_course_a = DocumentChunk(
        id="c1",
        document_id="doc1",
        course_id="course_A",
        chunk_index=0,
        page_number=1,
        content="Functional dependencies define attribute constraints in relational databases.",
        token_count=10,
        embedding=provider._generate_vector("Functional dependencies relational databases"),
        metadata_attributes={"source_filename": "notes_A.pdf"},
    )
    chunk_course_b = DocumentChunk(
        id="c2",
        document_id="doc2",
        course_id="course_B",
        chunk_index=0,
        page_number=1,
        content="Confidential exam questions for course B with relational functional dependencies.",
        token_count=10,
        embedding=provider._generate_vector("Confidential exam relational functional dependencies"),
        metadata_attributes={"source_filename": "secret_B.pdf"},
    )

    # Query strictly for course_A
    result_a = KnowledgeRetrievalEngine.retrieve_chunks(
        query="Functional dependencies",
        query_vector=q_vec,
        chunks=[chunk_course_a, chunk_course_b],
        course_id="course_A",
        similarity_threshold=0.20,
    )

    assert result_a.course_id == "course_A"
    assert len(result_a.matches) == 1
    assert result_a.matches[0].chunk_id == "c1"
    # Never leaks course_B content
    assert all(m.chunk_id != "c2" for m in result_a.matches)
    assert "[Lecture: notes_A.pdf, Page 1]" in result_a.matches[0].citation


@pytest.mark.unit
def test_honest_abstention_on_irrelevant_query() -> None:
    provider = DeterministicMockEmbeddingProvider()
    q_vec = provider._generate_vector("Photosynthesis chlorophyll plant biology")

    chunk = DocumentChunk(
        id="c1",
        document_id="doc1",
        course_id="cs340",
        chunk_index=0,
        page_number=1,
        content="Relational schema normalization: 1NF, 2NF, 3NF, and Boyce-Codd Normal Form.",
        token_count=12,
        embedding=provider._generate_vector("Relational schema normalization normal forms"),
        metadata_attributes={"source_filename": "dbms.pdf"},
    )

    result = KnowledgeRetrievalEngine.retrieve_chunks(
        query="Photosynthesis",
        query_vector=q_vec,
        chunks=[chunk],
        course_id="cs340",
        similarity_threshold=0.50,
    )

    assert result.abstention_recommended
    assert len(result.matches) == 0
    assert "recommends abstaining" in result.explanation
