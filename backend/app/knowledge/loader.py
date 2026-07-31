"""
Document loader for extracting text from different file types.
Supports PDF, TXT, MD, DOCX, and Source Code.
"""

import io
import os
import pypdf
import docx2txt
from app.core.logging import get_logger

logger = get_logger(__name__)


class UnsupportedFileTypeError(Exception):
    """Exception raised when an unsupported file type is provided."""
    pass


class DocumentLoader:
    """
    Parses document bytes into raw text based on the file type.
    """

    SUPPORTED_EXTENSIONS = {
        # PDF
        ".pdf",
        # Word
        ".docx",
        # Plain Text & MD
        ".txt", ".md", ".markdown",
        # Source Code / Configs
        ".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css",
        ".json", ".yaml", ".yml", ".ini", ".toml", ".sql",
        ".sh", ".bat", ".ps1", ".go", ".rs", ".java", ".cpp",
        ".c", ".h", ".cs", ".rb", ".php", ".kt", ".swift",
    }

    @classmethod
    def is_supported(cls, filename: str) -> bool:
        """Check if the file type is supported based on its extension."""
        ext = os.path.splitext(filename.lower())[1]
        return ext in cls.SUPPORTED_EXTENSIONS

    async def load(self, filename: str, content_bytes: bytes) -> str:
        """
        Loads document bytes and extracts text.

        Args:
            filename: Name of the file being loaded.
            content_bytes: Raw file content.

        Returns:
            Extracted clean text string.

        Raises:
            UnsupportedFileTypeError: If file extension is not supported.
            Exception: If parsing fails.
        """
        ext = os.path.splitext(filename.lower())[1]
        logger.info("Loading document: %s (size: %d bytes, ext: %s)", filename, len(content_bytes), ext)

        if not self.is_supported(filename):
            logger.error("Unsupported file type: %s", ext)
            raise UnsupportedFileTypeError(f"Unsupported file type: {ext}")

        try:
            if ext == ".pdf":
                return await self._load_pdf(content_bytes)
            elif ext == ".docx":
                return await self._load_docx(content_bytes)
            else:
                # Text, MD, and all source code files are parsed as plain text
                return await self._load_text(content_bytes)
        except Exception as e:
            logger.exception("Failed to parse file %s: %s", filename, e)
            raise

    async def _load_pdf(self, content_bytes: bytes) -> str:
        """Extract text from PDF bytes."""
        text_parts = []
        try:
            pdf_file = io.BytesIO(content_bytes)
            reader = pypdf.PdfReader(pdf_file)
            for page_num, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            
            extracted_text = "\n".join(text_parts)
            if not extracted_text.strip():
                logger.warning("PDF extraction returned empty text.")
            return extracted_text
        except Exception as e:
            logger.error("Error reading PDF: %s", e)
            raise ValueError(f"Failed to parse PDF document: {e}") from e

    async def _load_docx(self, content_bytes: bytes) -> str:
        """Extract text from DOCX bytes."""
        try:
            docx_file = io.BytesIO(content_bytes)
            text = docx2txt.process(docx_file)
            return text or ""
        except Exception as e:
            logger.error("Error reading DOCX: %s", e)
            raise ValueError(f"Failed to parse Word document: {e}") from e

    async def _load_text(self, content_bytes: bytes) -> str:
        """Extract text from plain text/source files using UTF-8 with Latin-1 fallback."""
        try:
            return content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            logger.warning("UTF-8 decoding failed, falling back to Latin-1")
            return content_bytes.decode("latin-1")
