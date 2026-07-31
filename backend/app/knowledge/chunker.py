"""
Document chunker for dividing text into overlapping segments.
"""

from app.core.logging import get_logger

logger = get_logger(__name__)


class DocumentChunker:
    """
    Splits raw document text into chunks of predefined sizes with overlapping windows.
    """

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 100) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("Chunk overlap must be strictly less than chunk size")

    def chunk(self, text: str) -> list[str]:
        """
        Splits the given text into chunks.

        Args:
            text: Raw input text.

        Returns:
            List of text chunks.
        """
        if not text or not text.strip():
            return []

        chunks = []
        text_length = len(text)
        start = 0

        while start < text_length:
            end = start + self.chunk_size

            # If we're not at the end of the text, try to find a natural boundary (newline or space)
            # within the last 20% of the chunk size to avoid splitting words.
            if end < text_length:
                boundary_search_start = max(start + int(self.chunk_size * 0.8), end - 50)
                # Look for last space or newline in this search window
                idx = text.rfind(" ", boundary_search_start, end)
                if idx == -1:
                    idx = text.rfind("\n", boundary_search_start, end)
                
                if idx != -1:
                    end = idx + 1 # Include the space or newline

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            # Move start window forward
            start = end - self.chunk_overlap
            
            # Prevent infinite loops if start isn't advancing
            if start >= text_length or (end - start) <= 0:
                break

        logger.info("Chunked text into %d segments (size: %d, overlap: %d)", len(chunks), self.chunk_size, self.chunk_overlap)
        return chunks
