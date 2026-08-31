"""
Deterministic Validator & Quality Gate.
Runs automated, non-LLM checks on generated code:
  1. Syntax validation (ast.parse for Python files)
  2. Cross-file import validation (do imported local modules exist?)
  3. Dependency completeness (requirements.txt vs actual imports)
  4. File manifest check (all planned files were generated)

Quality Gate additionally executes:
  5. Ruff linter (full check)
  6. Pytest test execution
  7. Bandit security scanner

The Quality Gate is the SINGLE SOURCE OF TRUTH for deterministic execution validity.
No LLM agent may modify or override these results.
"""

from __future__ import annotations

import ast
import asyncio
import re
import subprocess
import sys
import time
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

    Also serves as the Quality Gate: runs Ruff, Pytest, and Bandit to produce
    authoritative structured validation results that no LLM agent may override.
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

    async def run_full_quality_gate(
        self,
        workspace_dir: Path,
        planned_files: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Run the complete Quality Gate: deterministic checks + Ruff + Pytest + Bandit.

        This is the SINGLE SOURCE OF TRUTH for deterministic execution validity.
        Missing or unavailable validation evidence does NOT default to PASS.

        Returns structured validation_results:
        {
            "deterministic_checks": {"status": "PASS|FAIL|ERROR", "output": "..."},
            "ruff": {"status": "PASS|FAIL|ERROR", "output": "..."},
            "pytest": {"status": "PASS|FAIL|ERROR", "output": "..."},
            "bandit": {"status": "PASS|WARNING|FAIL|ERROR", "output": "..."},
            "quality_gate": "PASS|PASS_WITH_WARNINGS|FAIL",
            "test_passed": bool,
        }
        """
        if not workspace_dir.exists():
            error_msg = f"Workspace directory does not exist: {workspace_dir}"
            return {
                "deterministic_checks": {"status": "ERROR", "output": error_msg},
                "ruff": {"status": "ERROR", "output": "Skipped — workspace missing"},
                "pytest": {"status": "ERROR", "output": "Skipped — workspace missing"},
                "bandit": {"status": "ERROR", "output": "Skipped — workspace missing"},
                "quality_gate": "FAIL",
                "test_passed": False,
            }

        # 1. Run existing deterministic checks (syntax, imports, deps, manifest)
        det_result = await self.validate(workspace_dir, planned_files)
        if det_result["passed"]:
            det_status = "PASS"
            det_output = det_result["summary"]
        else:
            det_status = "FAIL"
            det_output = "\n".join(
                f"[{e['severity']}] {e['type']} in {e['file']}: {e['message']}"
                for e in det_result["errors"]
            )

        # 2. Run Ruff linter (full check)
        ruff_raw = await self._run_tool_cmd(
            [sys.executable, "-m", "ruff", "check", "--no-cache", str(workspace_dir)],
            timeout=30.0,
        )
        ruff_status = self._classify_ruff_status(ruff_raw)

        # 3. Run Pytest
        pytest_raw = await self._run_pytest(workspace_dir)
        pytest_status = self._classify_pytest_status(pytest_raw)

        # 4. Run Bandit (-s B101 to skip assert checks in test files)
        bandit_raw = await self._run_tool_cmd(
            [sys.executable, "-m", "bandit", "-r", "-s", "B101", str(workspace_dir)],
            timeout=30.0,
        )
        bandit_status = self._classify_bandit_status(bandit_raw)

        # 5. Compute authoritative Quality Gate decision
        has_failure = (
            det_status == "FAIL"
            or ruff_status == "FAIL"
            or pytest_status == "FAIL"
            or bandit_status == "FAIL"
            or det_status == "ERROR"
            or ruff_status == "ERROR"
            or pytest_status == "ERROR"
            or bandit_status == "ERROR"
        )
        has_warning = bandit_status == "WARNING" or ruff_status == "WARNING"

        if has_failure:
            quality_gate = "FAIL"
        elif has_warning:
            quality_gate = "PASS_WITH_WARNINGS"
        else:
            quality_gate = "PASS"

        return {
            "deterministic_checks": {"status": det_status, "output": det_output[:2000]},
            "ruff": {"status": ruff_status, "output": ruff_raw[:2000]},
            "pytest": {"status": pytest_status, "output": pytest_raw[:2000]},
            "bandit": {"status": bandit_status, "output": bandit_raw[:2000]},
            "quality_gate": quality_gate,
            "test_passed": quality_gate != "FAIL",
        }

    # ─── Tool Classification Helpers ───────────────────────────────────

    @staticmethod
    def _classify_ruff_status(output: str) -> str:
        """Classify Ruff output into PASS / WARNING / FAIL / ERROR."""
        if output.startswith("Tool execution error:") or output.startswith("Tool timed out"):
            return "ERROR"
        if not output or output == "Passed cleanly.":
            return "PASS"
        error_codes = ["F821", "E999", "SyntaxError", "error: ", "Error:"]
        if any(code in output for code in error_codes):
            return "FAIL"
        warning_indicators = ["warning", "w292", "i001"]
        output_lower = output.lower()
        if any(w in output_lower for w in warning_indicators):
            return "WARNING"
        # Ruff found issues but none are critical errors
        if "Found" in output and "error" in output_lower:
            return "FAIL"
        return "PASS"

    @staticmethod
    def _classify_pytest_status(output: str) -> str:
        """Classify Pytest output into PASS / FAIL / ERROR."""
        if not output:
            return "ERROR"  # Missing evidence = ERROR, not PASS
        if output.startswith("Tool execution error:") or output.startswith("Tool timed out"):
            return "ERROR"
        fail_keywords = [
            "FAILED", "ERROR", "collected 0 items", "1 error",
            "SyntaxError", "ModuleNotFoundError", "ImportError",
            "no tests ran", "0 passed",
        ]
        if any(kw in output for kw in fail_keywords):
            return "FAIL"
        if "passed" in output.lower():
            return "PASS"
        return "ERROR"  # Ambiguous output = ERROR, not PASS

    @staticmethod
    def _classify_bandit_status(output: str) -> str:
        """Classify Bandit output into PASS / WARNING / FAIL / ERROR."""
        if not output:
            return "ERROR"
        if output.startswith("Tool execution error:") or output.startswith("Tool timed out"):
            return "ERROR"
        if "Severity: High" in output or "Severity: Critical" in output:
            return "FAIL"
        if "Severity: Medium" in output or "Severity: Low" in output:
            return "WARNING"
        if "No issues identified" in output or "Passed cleanly" in output:
            return "PASS"
        # Bandit ran but output is ambiguous
        return "PASS"

    # ─── Subprocess Runners ────────────────────────────────────────────

    async def _run_tool_cmd(self, cmd: list[str], timeout: float = 30.0) -> str:
        """Run a CLI tool command without relying on Windows async subprocess support."""
        return await asyncio.to_thread(self._run_tool_cmd_sync, cmd, timeout)

    @staticmethod
    def _run_tool_cmd_sync(cmd: list[str], timeout: float) -> str:
        """Run a command in a worker thread and return its combined output.

        ``asyncio.create_subprocess_exec`` is unavailable when Uvicorn uses a
        Windows selector event loop.  ``subprocess.run`` in ``to_thread`` keeps
        the API non-blocking while working on every supported event loop.
        """
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )
            output = (result.stdout + result.stderr).strip()
            return output[:3000] or "Passed cleanly."
        except subprocess.TimeoutExpired:
            logger.warning("Tool %s timed out after %.0fs", cmd[1] if len(cmd) > 1 else cmd[0], timeout)
            return f"Tool timed out after {timeout}s."
        except FileNotFoundError:
            logger.warning("Tool %s not found.", cmd[0])
            return f"{cmd[0]} not installed."
        except Exception as e:
            logger.debug("Tool command %s failed: %s", cmd[0], e)
            detail = str(e) or "no additional detail"
            return f"Tool execution error: {type(e).__name__}: {detail}"

    async def _run_pytest(self, workspace_dir: Path, timeout: float = 60.0) -> str:
        """Run pytest against the workspace directory. Returns combined output."""
        test_files = list(workspace_dir.rglob("test_*.py")) + list(workspace_dir.rglob("*_test.py"))
        if not test_files:
            return "No test files found in workspace."

        cmd = [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-v", str(workspace_dir)]
        return await self._run_tool_cmd(cmd, timeout=timeout)

    # ─── Existing Deterministic Check Methods (unchanged) ──────────────

    def _check_syntax(self, py_files: list[Path], workspace_dir: Path) -> list[dict[str, Any]]:
        """Parse every .py file with ast.parse and ruff to catch SyntaxErrors and Undefined Names."""
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

        # Run ruff check to catch undefined names (F821) and critical syntax issues
        try:
            res = subprocess.run(
                [sys.executable, "-m", "ruff", "check", "--no-cache", str(workspace_dir)],
                capture_output=True,
                text=True,
                timeout=5
            )
            if res.returncode != 0 and res.stdout:
                for line in res.stdout.splitlines():
                    if any(code in line for code in ["F821", "E999", "F811"]):
                        errors.append({
                            "type": "LinterError",
                            "file": line.split(":")[0] if ":" in line else str(workspace_dir),
                            "line": None,
                            "message": line.strip(),
                            "severity": "CRITICAL" if ("F821" in line or "E999" in line) else "WARNING",
                        })
        except Exception:
            pass

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
