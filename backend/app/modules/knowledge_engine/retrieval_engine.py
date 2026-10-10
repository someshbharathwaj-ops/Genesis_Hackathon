"""Course-isolated semantic vector retrieval with grounding verification and abstention."""

import math
from dataclasses import dataclass
from typing import Any

from app.models.document import DocumentChunk


@dataclass
class RetrievalMatch:
    """A matched passage with verifiable citation and similarity score."""

    chunk_id: str
    document_id: str
    document_filename: str
    page_number: int
    content: str
    similarity_score: float
    citation: str
    metadata_attributes: dict[str, Any]


@dataclass
class RetrievalResult:
    """Structured outcome of course-scoped retrieval with abstention advice."""

    query: str
    course_id: str
    total_candidates: int
    matches: list[RetrievalMatch]
    abstention_recommended: bool
    explanation: str


def compute_cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Compute cosine similarity between two float vectors."""
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0

    dot_product = sum(a * b for a, b in zip(vec1, vec2, strict=False))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))

    if norm1 < 1e-9 or norm2 < 1e-9:
        return 0.0

    sim = dot_product / (norm1 * norm2)
    return round(max(-1.0, min(1.0, sim)), 4)


class KnowledgeRetrievalEngine:
    """Retrieval engine executing similarity searches strictly within course boundaries."""

    DEFAULT_SIMILARITY_THRESHOLD: float = 0.25
    DEFAULT_TOP_K: int = 5

    @classmethod
    def retrieve_chunks(
        cls,
        query: str,
        query_vector: list[float],
        chunks: list[DocumentChunk],
        course_id: str,
        top_k: int = DEFAULT_TOP_K,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    ) -> RetrievalResult:
        """Score candidate chunks within course_id and return ranked matches with citations.

        Strict course isolation: Any chunk not matching course_id is rejected.
        Abstention protocol: If no chunk satisfies similarity_threshold, the engine
        honestly flags abstention_recommended=True.
        """
        # Strict isolation check
        isolated_chunks = [c for c in chunks if c.course_id == course_id and c.embedding]

        candidates: list[tuple[float, DocumentChunk]] = []
        for chunk in isolated_chunks:
            if chunk.embedding:
                score = compute_cosine_similarity(query_vector, chunk.embedding)
                if score >= similarity_threshold:
                    candidates.append((score, chunk))

        # Sort descending by score
        candidates.sort(key=lambda x: x[0], reverse=True)
        top_candidates = candidates[:top_k]

        matches: list[RetrievalMatch] = []
        for score, chunk in top_candidates:
            filename = (
                chunk.document.filename
                if chunk.document
                else chunk.metadata_attributes.get("source_filename", "Lecture Note")
            )
            citation = f"[Lecture: {filename}, Page {chunk.page_number}]"

            matches.append(
                RetrievalMatch(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    document_filename=filename,
                    page_number=chunk.page_number,
                    content=chunk.content,
                    similarity_score=score,
                    citation=citation,
                    metadata_attributes=chunk.metadata_attributes,
                )
            )

        if not matches:
            abstention_recommended = True
            explanation = (
                f"No verified curriculum chunks in course '{course_id}' met the similarity "
                f"threshold ({similarity_threshold:.2f}) for query '{query}'. "
                "System recommends abstaining to prevent hallucination."
            )
        else:
            abstention_recommended = False
            top_score = matches[0].similarity_score
            explanation = (
                f"Retrieved {len(matches)} relevant chunk(s) for query '{query}' "
                f"(top similarity: {top_score:.2f}). Citations grounded in course materials."
            )

        return RetrievalResult(
            query=query,
            course_id=course_id,
            total_candidates=len(isolated_chunks),
            matches=matches,
            abstention_recommended=abstention_recommended,
            explanation=explanation,
        )
