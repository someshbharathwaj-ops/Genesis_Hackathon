"""Knowledge Engine module: document ingestion, extraction, chunking, and course-isolated RAG."""

from app.modules.knowledge_engine.chunker import DocumentChunkItem, SemanticChunker
from app.modules.knowledge_engine.document_extractor import (
    DocumentExtractionResult,
    DocumentExtractor,
)
from app.modules.knowledge_engine.embedding_provider import (
    BaseEmbeddingProvider,
    DeterministicMockEmbeddingProvider,
    OllamaEmbeddingProvider,
    get_embedding_provider,
)
from app.modules.knowledge_engine.retrieval_engine import (
    KnowledgeRetrievalEngine,
    RetrievalMatch,
    RetrievalResult,
)

__all__ = [
    "DocumentExtractionResult",
    "DocumentExtractor",
    "DocumentChunkItem",
    "SemanticChunker",
    "BaseEmbeddingProvider",
    "DeterministicMockEmbeddingProvider",
    "OllamaEmbeddingProvider",
    "get_embedding_provider",
    "KnowledgeRetrievalEngine",
    "RetrievalMatch",
    "RetrievalResult",
]
