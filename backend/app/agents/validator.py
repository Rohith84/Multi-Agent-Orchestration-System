"""
Deterministic Validator.
Runs automated, non-LLM checks on generated code:
  1. Syntax validation (ast.parse for Python files)
  2. Cross-file import validation (do imported local modules exist?)
  3. Dependency completeness (requirements.txt vs actual imports)
  4. File manifest check (all planned files were generated)
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

# Standard library module names (Python 3.10+) — used to filter out stdlib imports
_STDLIB_TOP_LEVEL: set[str] | None = None


def _get_stdlib_modules() -> set[str]:
    """Return a set of top-level stdlib module names."""
    global _STDLIB_TOP_LEVEL
    if _STDLIB_TOP_LEVEL is not None:
        return _STDLIB_TOP_LEVEL

    try:
        if sys.version_info >= (3, 10):
            _STDLIB_TOP_LEVEL = set(sys.stdlib_module_names)
        else:
            import pkgutil
            _STDLIB_TOP_LEVEL = {m.name for m in pkgutil.iter_modules() if m.ispkg is False}
    except Exception:
        _STDLIB_TOP_LEVEL = set()

    # Always include common builtins
    _STDLIB_TOP_LEVEL.update({
        "os", "sys", "re", "json", "typing", "pathlib", "datetime", "time",
        "math", "collections", "itertools", "functools", "enum", "uuid",
        "hashlib", "base64", "io", "abc", "logging", "unittest", "asyncio",
        "dataclasses", "contextlib", "copy", "shutil", "tempfile", "textwrap",
        "traceback", "warnings", "importlib", "inspect", "string", "struct",
    })
    return _STDLIB_TOP_LEVEL


class DeterministicValidator:
    """
    Runs automated, non-LLM checks on generated code files in a workspace directory.
    Returns a structured result with pass/fail status and specific errors.
    """

    async def validate(
        self,
        workspace_dir: Path,
        planned_files: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Run all deterministic checks and return results.

        Args:
            workspace_dir: Path to the sandbox workspace containing generated files.
            planned_files: Optional list of relative file paths that SHOULD exist (from Planner's manifest).

        Returns:
            Dictionary with 'passed' (bool), 'errors' (list), and 'summary' (str).
        """
        errors: list[dict[str, Any]] = []

        if not workspace_dir.exists():
            return {
                "passed": False,
                "errors": [{"type": "WorkspaceError", "file": str(workspace_dir), "line": None, "message": "Workspace directory does not exist", "severity": "CRITICAL"}],
                "summary": "Workspace directory does not exist",
            }

        py_files = list(workspace_dir.rglob("*.py"))

        # 1. Syntax validation
        syntax_errors = self._check_syntax(py_files, workspace_dir)
        errors.extend(syntax_errors)

        # 2. Cross-file import validation
        import_errors = self._check_imports(py_files, workspace_dir)
        errors.extend(import_errors)

        # 3. Dependency completeness
        dep_errors = self._check_dependencies(py_files, workspace_dir)
        errors.extend(dep_errors)

        # 4. File manifest check
        if planned_files:
            manifest_errors = self._check_manifest(planned_files, workspace_dir)
            errors.extend(manifest_errors)

        passed = len(errors) == 0
        critical_count = sum(1 for e in errors if e.get("severity") == "CRITICAL")
        warning_count = sum(1 for e in errors if e.get("severity") == "WARNING")

        summary = (
            "All deterministic checks passed"
            if passed
            else f"{critical_count} critical, {warning_count} warning issues found across {len(py_files)} files"
        )

        return {
            "passed": passed,
            "errors": errors,
            "summary": summary,
        }

    def _check_syntax(self, py_files: list[Path], workspace_dir: Path) -> list[dict[str, Any]]:
        """Parse every .py file with ast.parse to catch SyntaxErrors."""
        errors = []
        for py_file in py_files:
            try:
                source = py_file.read_text(encoding="utf-8", errors="replace")
                ast.parse(source, filename=str(py_file.relative_to(workspace_dir)))
            except SyntaxError as e:
                errors.append({
                    "type": "SyntaxError",
                    "file": str(py_file.relative_to(workspace_dir)),
                    "line": e.lineno,
                    "message": str(e.msg),
                    "severity": "CRITICAL",
                })
            except Exception as e:
                errors.append({
                    "type": "ParseError",
                    "file": str(py_file.relative_to(workspace_dir)),
                    "line": None,
                    "message": str(e),
                    "severity": "WARNING",
                })
        return errors

    def _check_imports(self, py_files: list[Path], workspace_dir: Path) -> list[dict[str, Any]]:
        """Check that locally-referenced imports correspond to existing files in the workspace."""
        errors = []

        # Build set of all module names available in workspace
        available_modules: set[str] = set()
        for py_file in py_files:
            rel = py_file.relative_to(workspace_dir)
            parts = list(rel.with_suffix("").parts)
            # Register all prefix paths as module names (e.g., app.models.task -> app, app.models, app.models.task)
            for i in range(1, len(parts) + 1):
                available_modules.add(".".join(parts[:i]))
            # Also register just the filename stem
            available_modules.add(rel.stem)

        stdlib = _get_stdlib_modules()

        for py_file in py_files:
            try:
                source = py_file.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(source)
            except (SyntaxError, Exception):
                continue  # Already caught in syntax check

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        top_level = alias.name.split(".")[0]
                        if top_level not in stdlib and top_level not in available_modules:
                            # Could be a third-party package — not necessarily an error
                            pass
                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.level == 0:
                        top_level = node.module.split(".")[0]
                        # Check if it's a local relative import that doesn't exist
                        if (
                            top_level not in stdlib
                            and node.module in available_modules
                        ):
                            # This is fine — local module exists
                            pass
                        elif top_level not in stdlib and top_level not in available_modules:
                            # Could be third-party — check if it's referenced as a local path
                            module_path = workspace_dir / node.module.replace(".", "/")
                            if (
                                not module_path.with_suffix(".py").exists()
                                and not (module_path / "__init__.py").exists()
                            ):
                                # Likely third-party, not a broken import — skip
                                pass

        return errors

    def _check_dependencies(self, py_files: list[Path], workspace_dir: Path) -> list[dict[str, Any]]:
        """Check that a requirements.txt exists if third-party packages are imported."""
        errors = []
        stdlib = _get_stdlib_modules()

        third_party_imports: set[str] = set()
        available_modules: set[str] = set()
        for py_file in py_files:
            available_modules.add(py_file.relative_to(workspace_dir).parts[0] if len(py_file.relative_to(workspace_dir).parts) > 1 else py_file.stem)

        for py_file in py_files:
            try:
                source = py_file.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(source)
            except (SyntaxError, Exception):
                continue

            for node in ast.walk(tree):
                module_name = None
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module_name = alias.name.split(".")[0]
                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.level == 0:
                        module_name = node.module.split(".")[0]

                if module_name and module_name not in stdlib and module_name not in available_modules:
                    third_party_imports.add(module_name)

        if third_party_imports:
            req_file = workspace_dir / "requirements.txt"
            if not req_file.exists():
                errors.append({
                    "type": "MissingDependencyFile",
                    "file": "requirements.txt",
                    "line": None,
                    "message": f"Project imports third-party packages ({', '.join(sorted(third_party_imports)[:5])}) but no requirements.txt was generated",
                    "severity": "WARNING",
                })

        return errors

    def _check_manifest(self, planned_files: list[str], workspace_dir: Path) -> list[dict[str, Any]]:
        """Check that every file in the Planner's manifest was actually created."""
        errors = []
        for planned in planned_files:
            clean_path = planned.strip().lstrip("/\\")
            target = workspace_dir / clean_path
            if not target.exists():
                errors.append({
                    "type": "MissingFile",
                    "file": clean_path,
                    "line": None,
                    "message": f"Planned file '{clean_path}' was not generated by the Coder",
                    "severity": "CRITICAL",
                })
        return errors
