"""
Artifact Extractor Utility.
Parses LLM text outputs to extract clean source code files and artifacts.
Guarantees natural language prose is never written into source files.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List


@dataclass
class CodeArtifact:
    path: str
    content: str
    language: str


# Valid file extensions for source code & configuration artifacts
VALID_EXTENSIONS = (
    ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".json",
    ".yaml", ".yml", ".toml", ".sh", ".bash", ".sql", ".env", ".md",
    "dockerfile", "requirements.txt"
)


def is_valid_filename(filename: str) -> bool:
    """Check if a string looks like a valid relative file path."""
    clean = filename.strip().strip("'\"`").lstrip("/\\")
    if not clean or any(c in clean for c in ["<", ">", ":", "*", "?", "|"]):
        return False
    lower = clean.lower()
    if lower == "dockerfile" or lower.endswith("dockerfile") or lower.endswith("requirements.txt"):
        return True
    return any(lower.endswith(ext) for ext in VALID_EXTENSIONS)


def clean_source_content(content: str) -> str:
    """Strip leading/trailing markdown code fences and whitespace."""
    lines = content.strip().splitlines()
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def extract_code_artifacts(text: str) -> List[CodeArtifact]:
    """
    Parses LLM text output and returns a list of CodeArtifact objects.
    Extracts ONLY source code blocks, filtering out natural language prose.
    """
    artifacts: List[CodeArtifact] = []
    if not text or not text.strip():
        return artifacts

    # Pattern 1: Code blocks with explicit filepath/file attribute in backtick line
    # e.g., ```python filepath="main.py" or ```python file='app/routes.py' or ```python file=main.py
    attr_pattern = r"```([a-zA-Z0-9_-]*)\s+(?:filepath|file)=[\"']?([^\"'\s\n>]+)[\"']?\s*\n(.*?)```"
    matched_ranges: List[tuple[int, int]] = []

    for match in re.finditer(attr_pattern, text, re.DOTALL):
        lang, rel_path, content = match.groups()
        clean_path = rel_path.strip().strip("'\"`").lstrip("/\\")
        clean_code = clean_source_content(content)
        if is_valid_filename(clean_path) and clean_code:
            artifacts.append(CodeArtifact(
                path=clean_path,
                content=clean_code,
                language=lang.strip().lower() or "python"
            ))
            matched_ranges.append((match.start(), match.end()))

    # Pattern 2: Generic code blocks ```[lang]\n[content]```
    generic_pattern = r"```([a-zA-Z0-9_-]*)\s*\n(.*?)```"
    for match in re.finditer(generic_pattern, text, re.DOTALL):
        # Skip if this block was already matched by attribute pattern
        if any(start <= match.start() < end for start, end in matched_ranges):
            continue

        lang, content = match.groups()
        clean_code = clean_source_content(content)
        if not clean_code:
            continue

        # Look for filename in first 3 lines of block content (comments)
        inferred_path = None
        lines = clean_code.splitlines()
        for i in range(min(3, len(lines))):
            line = lines[i].strip()
            # Match # filepath: app/main.py or # app/main.py or // app/main.py or -- app/main.py
            comment_match = re.search(
                r"^(?:#|//|--|/\*|<!--)\s*(?:filepath|file)?\s*[:=]?\s*([a-zA-Z0-9_./\\-]+\.[a-zA-Z0-9]+|dockerfile|requirements\.txt)",
                line,
                re.IGNORECASE
            )
            if comment_match:
                possible_path = comment_match.group(1).strip()
                if is_valid_filename(possible_path):
                    inferred_path = possible_path
                    lines = lines[:i] + lines[i+1:]
                    break

        # Look for filename in text immediately preceding code block (up to 200 chars back)
        if not inferred_path:
            preceding_text = text[max(0, match.start() - 200):match.start()]
            heading_matches = re.findall(r"(?:###|\*\*|`|File:)\s*([a-zA-Z0-9_./\\-]+\.[a-zA-Z0-9]+)", preceding_text)
            if heading_matches:
                possible_path = heading_matches[-1].strip().strip("`*")
                if is_valid_filename(possible_path):
                    inferred_path = possible_path

        # Fallback for single unannotated code block
        if not inferred_path:
            clean_lang = lang.strip().lower()
            if clean_lang in ("python", "py"):
                if "def test_" in clean_code or "import pytest" in clean_code or "class Test" in clean_code:
                    inferred_path = "test_suite.py"
                else:
                    inferred_path = "main.py"
            elif clean_lang in ("yaml", "yml"):
                inferred_path = "docker-compose.yml"
            elif clean_lang == "dockerfile":
                inferred_path = "Dockerfile"
            elif clean_lang in ("json",):
                inferred_path = "config.json"
            elif clean_lang in ("html",):
                inferred_path = "index.html"
            elif clean_lang in ("css",):
                inferred_path = "styles.css"
            elif clean_lang in ("js", "javascript"):
                inferred_path = "script.js"
            elif clean_lang in ("ts", "typescript"):
                inferred_path = "index.ts"

        if inferred_path and is_valid_filename(inferred_path):
            artifacts.append(CodeArtifact(
                path=inferred_path,
                content="\n".join(lines).strip(),
                language=lang.strip().lower() or "python"
            ))

    # Deduplicate by path (keep last occurrence as latest version)
    deduped: dict[str, CodeArtifact] = {}
    for art in artifacts:
        deduped[art.path] = art

    return list(deduped.values())
