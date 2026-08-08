"""
DLPScanner — Enterprise Data Loss Prevention (DLP) Secret Masking Engine.

Scans prompts and agent outputs for Passwords, Private Keys, Credit Cards, PII, and API Keys, redacting sensitive content automatically.
"""

from __future__ import annotations

import re
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

# DLP Regex Patterns for Sensitive Data Detection
DLP_PATTERNS = [
    (r"(?i)(api[_-]?key|secret[_-]?key|access[_-]?token)[\s=:\"]+([a-zA-Z0-9_\-]{16,})", r"\1: [REDACTED_API_KEY]"),
    (r"-----BEGIN (RSA|OPENSSH|EC|PRIVATE) KEY-----[\s\S]+?-----END \1 KEY-----", "[REDACTED_PRIVATE_KEY]"),
    (r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b", "[REDACTED_CREDIT_CARD]"),
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[REDACTED_EMAIL]"),
    (r"(?i)(password|passwd|pwd)[\s=:\"]+([^\s,]{4,})", r"\1: [REDACTED_PASSWORD]"),
]


class DLPScanner:
    """
    Scans text for sensitive enterprise secrets and PII data, returning clean redacted output.
    """

    def scan_and_sanitize(self, text: str) -> tuple[str, int]:
        """
        Scan text, redact secrets, and return (clean_text, detections_count).
        """
        sanitized = text
        detections = 0

        for pattern, replacement in DLP_PATTERNS:
            matches = len(re.findall(pattern, sanitized))
            if matches > 0:
                detections += matches
                sanitized = re.sub(pattern, replacement, sanitized)

        if detections > 0:
            logger.info("DLP Scanner masked %d sensitive secret/PII instances.", detections)

        return sanitized, detections
