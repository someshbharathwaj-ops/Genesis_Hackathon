"""Semantic chunking preserving page-level and structural provenance."""

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DocumentChunkItem:
    """A semantic chunk derived from a document page."""

    chunk_index: int
    page_number: int
    content: str
    token_count: int
    metadata_attributes: dict[str, Any] = field(default_factory=dict)


class SemanticChunker:
    """Splits document text into cohesive passages with preserved page provenance."""

    DEFAULT_TARGET_CHUNK_SIZE: int = 600
    DEFAULT_OVERLAP: int = 80

    @classmethod
    def chunk_document(
        cls,
        text_by_page: list[tuple[int, str]],
        filename: str,
        target_chunk_size: int = DEFAULT_TARGET_CHUNK_SIZE,
        overlap: int = DEFAULT_OVERLAP,
    ) -> list[DocumentChunkItem]:
        """Convert page-segmented text into a sequence of provenance-preserving chunks."""
        chunks: list[DocumentChunkItem] = []
        global_chunk_idx = 0

        for page_num, page_text in text_by_page:
            cleaned = page_text.strip()
            if not cleaned:
                continue

            # Split into paragraphs / logical blocks
            paragraphs = [p.strip() for p in re.split(r"\n\s*\n", cleaned) if p.strip()]
            if not paragraphs:
                paragraphs = [cleaned]

            current_chunk_parts: list[str] = []
            current_length = 0

            for para in paragraphs:
                # If paragraph fits in current chunk
                if current_length + len(para) <= target_chunk_size:
                    current_chunk_parts.append(para)
                    current_length += len(para) + 1
                else:
                    # Flush current chunk if non-empty
                    if current_chunk_parts:
                        chunk_text = "\n\n".join(current_chunk_parts).strip()
                        if chunk_text:
                            approx_tokens = len(chunk_text.split())
                            chunks.append(
                                DocumentChunkItem(
                                    chunk_index=global_chunk_idx,
                                    page_number=page_num,
                                    content=chunk_text,
                                    token_count=approx_tokens,
                                    metadata_attributes={
                                        "source_filename": filename,
                                        "page_number": page_num,
                                    },
                                )
                            )
                            global_chunk_idx += 1

                    # If paragraph itself exceeds target_chunk_size, split by sentences
                    if len(para) > target_chunk_size:
                        sub_chunks = cls._split_large_paragraph(
                            para, target_chunk_size, overlap
                        )
                        for sub_text in sub_chunks:
                            approx_tokens = len(sub_text.split())
                            chunks.append(
                                DocumentChunkItem(
                                    chunk_index=global_chunk_idx,
                                    page_number=page_num,
                                    content=sub_text,
                                    token_count=approx_tokens,
                                    metadata_attributes={
                                        "source_filename": filename,
                                        "page_number": page_num,
                                    },
                                )
                            )
                            global_chunk_idx += 1
                        current_chunk_parts = []
                        current_length = 0
                    else:
                        current_chunk_parts = [para]
                        current_length = len(para)

            # Flush remaining buffer for this page
            if current_chunk_parts:
                chunk_text = "\n\n".join(current_chunk_parts).strip()
                if chunk_text:
                    approx_tokens = len(chunk_text.split())
                    chunks.append(
                        DocumentChunkItem(
                            chunk_index=global_chunk_idx,
                            page_number=page_num,
                            content=chunk_text,
                            token_count=approx_tokens,
                            metadata_attributes={
                                "source_filename": filename,
                                "page_number": page_num,
                            },
                        )
                    )
                    global_chunk_idx += 1

        return chunks

    @classmethod
    def _split_large_paragraph(
        cls,
        text: str,
        max_size: int,
        overlap: int,
    ) -> list[str]:
        """Split a large paragraph into overlapping segments on sentence boundaries."""
        sentences = re.split(r"(?<=[.!?])\s+", text)
        result: list[str] = []
        current: list[str] = []
        current_len = 0

        for sentence in sentences:
            if current_len + len(sentence) <= max_size:
                current.append(sentence)
                current_len += len(sentence) + 1
            else:
                if current:
                    result.append(" ".join(current).strip())
                # Start new buffer with sentence or character slice
                if len(sentence) > max_size:
                    # Fallback word-level slice
                    words = sentence.split()
                    sub_buf: list[str] = []
                    sub_len = 0
                    for w in words:
                        if sub_len + len(w) <= max_size:
                            sub_buf.append(w)
                            sub_len += len(w) + 1
                        else:
                            if sub_buf:
                                result.append(" ".join(sub_buf).strip())
                            sub_buf = [w]
                            sub_len = len(w)
                    if sub_buf:
                        current = sub_buf
                        current_len = sub_len
                    else:
                        current = []
                        current_len = 0
                else:
                    current = [sentence]
                    current_len = len(sentence)

        if current:
            result.append(" ".join(current).strip())

        return result
