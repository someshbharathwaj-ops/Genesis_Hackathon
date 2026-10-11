"""Robust document text extraction supporting PDF and plain text formats."""

import io
import os
from dataclasses import dataclass

import pypdf
import pypdf.errors

from app.core.errors import (
    DocumentEncryptedError,
    DocumentExtractionError,
    UnsupportedDocumentFormatError,
)


@dataclass
class DocumentExtractionResult:
    """Outcome of document text extraction."""

    text_by_page: list[tuple[int, str]]  # list of (1-indexed page_number, page_text)
    page_count: int
    is_empty: bool


class DocumentExtractor:
    """Robust extractor extracting text page-by-page from course documents."""

    SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".markdown", ".docx", ".pptx"}

    @classmethod
    def extract_from_bytes(
        cls,
        file_bytes: bytes,
        filename: str,
        mime_type: str | None = None,
    ) -> DocumentExtractionResult:
        """Extract text from raw document bytes.

        Handles empty, corrupt, encrypted, and unsupported files safely.
        """
        if not file_bytes:
            return DocumentExtractionResult(text_by_page=[], page_count=0, is_empty=True)

        _, ext = os.path.splitext(filename.lower())

        if ext == ".pdf" or mime_type == "application/pdf":
            return cls._extract_pdf(file_bytes, filename)
        elif (
            ext in (".txt", ".md", ".markdown")
            or mime_type in ("text/plain", "text/markdown", "application/x-markdown")
        ):
            return cls._extract_txt(file_bytes)
        elif ext == ".docx" or mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            return cls._extract_docx(file_bytes, filename)
        elif ext == ".pptx" or mime_type == "application/vnd.openxmlformats-officedocument.presentationml.presentation":
            return cls._extract_pptx(file_bytes, filename)
        else:
            raise UnsupportedDocumentFormatError(ext or (mime_type or "unknown"))

    @classmethod
    def _extract_pdf(cls, file_bytes: bytes, filename: str) -> DocumentExtractionResult:
        stream = io.BytesIO(file_bytes)
        try:
            reader = pypdf.PdfReader(stream)
        except (pypdf.errors.PdfReadError, Exception) as exc:
            raise DocumentExtractionError(f"Corrupted or malformed PDF: {exc}") from exc

        # Check encryption
        if reader.is_encrypted:
            try:
                # Try empty password in case of standard unencrypted permissions
                decrypt_success = reader.decrypt("")
                if decrypt_success == 0:
                    raise DocumentEncryptedError(filename)
            except Exception as exc:
                raise DocumentEncryptedError(filename) from exc

        total_pages = len(reader.pages)
        if total_pages == 0:
            return DocumentExtractionResult(text_by_page=[], page_count=0, is_empty=True)

        extracted_pages: list[tuple[int, str]] = []
        for idx, page in enumerate(reader.pages):
            try:
                text = page.extract_text() or ""
                cleaned = text.strip()
                if cleaned:
                    extracted_pages.append((idx + 1, cleaned))
            except Exception as exc:
                # Log or tolerate single page read issues if others can be read
                raise DocumentExtractionError(
                    f"Error reading page {idx + 1} of '{filename}': {exc}"
                ) from exc

        is_empty = len(extracted_pages) == 0
        return DocumentExtractionResult(
            text_by_page=extracted_pages,
            page_count=total_pages,
            is_empty=is_empty,
        )

    @classmethod
    def _extract_txt(cls, file_bytes: bytes) -> DocumentExtractionResult:
        try:
            text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = file_bytes.decode("latin-1")
            except Exception as exc:
                raise DocumentExtractionError(f"Encoding decode failure: {exc}") from exc

        cleaned = text.strip()
        if not cleaned:
            return DocumentExtractionResult(text_by_page=[], page_count=1, is_empty=True)

        return DocumentExtractionResult(
            text_by_page=[(1, cleaned)],
            page_count=1,
            is_empty=False,
        )

    @classmethod
    def _extract_docx(cls, file_bytes: bytes, filename: str) -> DocumentExtractionResult:
        import zipfile
        import xml.etree.ElementTree as ET

        try:
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
                xml_content = z.read("word/document.xml")
                tree = ET.fromstring(xml_content)
                text = " ".join(tree.itertext()).strip()
                if not text:
                    return DocumentExtractionResult(text_by_page=[], page_count=0, is_empty=True)
                return DocumentExtractionResult(
                    text_by_page=[(1, text)],
                    page_count=1,
                    is_empty=False,
                )
        except Exception as exc:
            raise DocumentExtractionError(f"Error extracting DOCX '{filename}': {exc}") from exc

    @classmethod
    def _extract_pptx(cls, file_bytes: bytes, filename: str) -> DocumentExtractionResult:
        import zipfile
        import xml.etree.ElementTree as ET

        try:
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
                slide_names = sorted(
                    [
                        name
                        for name in z.namelist()
                        if name.startswith("ppt/slides/slide") and name.endswith(".xml")
                    ],
                    key=lambda x: int("".join(filter(str.isdigit, x)) or "0"),
                )
                if not slide_names:
                    return DocumentExtractionResult(text_by_page=[], page_count=0, is_empty=True)
                pages: list[tuple[int, str]] = []
                for idx, sname in enumerate(slide_names):
                    tree = ET.fromstring(z.read(sname))
                    txt = " ".join(tree.itertext()).strip()
                    if txt:
                        pages.append((idx + 1, txt))
                return DocumentExtractionResult(
                    text_by_page=pages,
                    page_count=len(slide_names),
                    is_empty=len(pages) == 0,
                )
        except Exception as exc:
            raise DocumentExtractionError(f"Error extracting PPTX '{filename}': {exc}") from exc

