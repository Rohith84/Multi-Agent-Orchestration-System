"""
PromptSecurityScanner — Prompt Injection & Jailbreak Defense Shield.

Detects malicious prompt injection, system prompt extraction, instruction override, and tool abuse attempts.
"""

from __future__ import annotations

import re
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

PROMPT_INJECTION_PATTERNS = [
    r"(?i)ignore (previous|all|above) (instructions|directives|prompts)",
    r"(?i)disregard (previous|all|above) (rules|instructions)",
    r"(?i)reveal (your|system) (prompt|instructions|system_prompt)",
    r"(?i)you are now (in DAN mode|unrestricted|god mode)",
    r"(?i)override (safety|security|system) settings",
]


class PromptSecurityScanner:
    """
    Scans user inputs for prompt injection attack patterns.
    """

    def scan_prompt(self, user_prompt: str) -> dict[str, Any]:
        """
        Scan input text and return threat evaluation report.
        """
        threats_found = []

        for pattern in PROMPT_INJECTION_PATTERNS:
            if re.search(pattern, user_prompt):
                threats_found.append(pattern)

        is_malicious = len(threats_found) > 0

        if is_malicious:
            logger.warning("Prompt Injection attack detected! Patterns matched: %s", threats_found)

        return {
            "is_safe": not is_malicious,
            "threats_count": len(threats_found),
            "threat_patterns": threats_found,
            "recommendation": "BLOCK" if is_malicious else "ALLOW",
        }
