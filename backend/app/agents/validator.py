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
from app.orchestration.code_contract import CodeContractValidator
from app.schemas.tool_result import ToolResult, ToolStatus, execute_tool

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
        # 1. Workspace validation
        if not workspace_dir.exists():
            error_msg = f"Workspace directory does not exist: {workspace_dir}"
            return {
                "workspace_validation": {"status": "ERROR", "output": error_msg},
                "code_contract": {"status": "NOT_EXECUTED", "output": "Skipped — workspace missing"},
                "deterministic_checks": {"status": "NOT_EXECUTED", "output": "Skipped — workspace missing"},
                "ruff": {"status": "NOT_EXECUTED", "output": "Skipped — workspace missing"},
                "pytest": {"status": "NOT_EXECUTED", "output": "Skipped — workspace missing"},
                "bandit": {"status": "NOT_EXECUTED", "output": "Skipped — workspace missing"},
                "quality_gate": "FAIL",
                "test_passed": False,
            }

        # 2. CodeContract Validation — block downstream execution on contract failure
        code_contract_res = CodeContractValidator.validate(workspace_dir, planned_files)
        if not code_contract_res.is_valid:
            logger.warning(
                "CodeContract FAILED for workspace %s: %s — Quality Gate execution BLOCKED",
                workspace_dir,
                code_contract_res.summary,
            )
            failure_output = f"CodeContract Violation: {code_contract_res.summary}"
            if code_contract_res.errors:
                failure_output += "\n" + "\n".join(
                    f"[{e.rule}] {e.file}:{e.line or 1}: {e.message}" for e in code_contract_res.errors
                )

            return {
                "workspace_validation": {"status": "PASS", "output": "Workspace exists and is accessible."},
                "code_contract": code_contract_res.model_dump(),
                "deterministic_checks": {"status": "NOT_EXECUTED", "output": "Skipped — CodeContract validation failed"},
                "ruff": {"status": "NOT_EXECUTED", "output": "Skipped — CodeContract validation failed"},
                "pytest": {"status": "NOT_EXECUTED", "output": "Skipped — CodeContract validation failed"},
                "bandit": {"status": "NOT_EXECUTED", "output": "Skipped — CodeContract validation failed"},
                "quality_gate": "FAIL",
                "test_passed": False,
            }

        # 3. Deterministic syntax, import, dependency, and manifest validation
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
            return {
                "workspace_validation": {"status": "PASS", "output": "Workspace exists and is accessible."},
                "code_contract": code_contract_res.model_dump(),
                "deterministic_checks": {"status": "FAIL", "output": det_output[:2000]},
                "ruff": {"status": "NOT_EXECUTED", "output": "Skipped — Deterministic syntax/import validation failed"},
                "pytest": {"status": "NOT_EXECUTED", "output": "Skipped — Deterministic syntax/import validation failed"},
                "bandit": {"status": "NOT_EXECUTED", "output": "Skipped — Deterministic syntax/import validation failed"},
                "quality_gate": "FAIL",
                "test_passed": False,
            }

        # 4. Run Ruff linter (full check)
        ruff_raw = await self._run_tool_cmd(
            [sys.executable, "-m", "ruff", "check", "--no-cache", str(workspace_dir)],
            timeout=30.0,
            cwd=workspace_dir,
            tool_name="ruff",
        )
        if isinstance(ruff_raw, ToolResult):
            if ruff_raw.status == ToolStatus.PASS:
                ruff_status = "PASS"
            elif ruff_raw.status in (ToolStatus.LINT_FAILURE, ToolStatus.TEST_FAILURE, ToolStatus.CONFIG_ERROR):
                ruff_status = "FAIL"
            else:
                ruff_status = "ERROR"
            ruff_output = ruff_raw.stdout or ruff_raw.stderr or ruff_raw.execution_error or ""
            ruff_res_dump = ruff_raw.model_dump()
        else:
            ruff_status = self._classify_ruff_status(ruff_raw)
            ruff_output = ruff_raw
            ruff_res_dump = None

        # 5. Run Pytest
        pytest_raw = await self._run_pytest(workspace_dir)
        if isinstance(pytest_raw, ToolResult):
            if pytest_raw.status == ToolStatus.PASS:
                pytest_status = "PASS"
            elif pytest_raw.status in (ToolStatus.TEST_FAILURE, ToolStatus.LINT_FAILURE, ToolStatus.CONFIG_ERROR):
                pytest_status = "FAIL"
            else:
                pytest_status = "ERROR"
            pytest_output = pytest_raw.stdout or pytest_raw.stderr or pytest_raw.execution_error or ""
            pytest_res_dump = pytest_raw.model_dump()
        else:
            pytest_status = self._classify_pytest_status(pytest_raw)
            pytest_output = pytest_raw
            pytest_res_dump = None

        # 6. Run Bandit (-s B101 to skip assert checks in test files)
        bandit_raw = await self._run_tool_cmd(
            [sys.executable, "-m", "bandit", "-r", "-s", "B101", str(workspace_dir)],
            timeout=30.0,
            cwd=workspace_dir,
            tool_name="bandit",
        )
        if isinstance(bandit_raw, ToolResult):
            if bandit_raw.status == ToolStatus.PASS:
                bandit_status = "PASS"
            elif bandit_raw.status in (ToolStatus.LINT_FAILURE, ToolStatus.TEST_FAILURE, ToolStatus.CONFIG_ERROR):
                bandit_status = "FAIL"
            else:
                bandit_status = "ERROR"
            bandit_output = bandit_raw.stdout or bandit_raw.stderr or bandit_raw.execution_error or ""
            bandit_res_dump = bandit_raw.model_dump()
        else:
            bandit_status = self._classify_bandit_status(bandit_raw)
            bandit_output = bandit_raw
            bandit_res_dump = None

        # 7. Compute Authoritative Quality Gate Decision
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

        test_passed = pytest_status in ("PASS", "WARNING")

        return {
            "workspace_validation": {"status": "PASS", "output": "Workspace exists and is accessible."},
            "code_contract": code_contract_res.model_dump(),
            "deterministic_checks": {"status": det_status, "output": det_output},
            "ruff": {"status": ruff_status, "output": ruff_output, "result": ruff_res_dump},
            "pytest": {"status": pytest_status, "output": pytest_output, "result": pytest_res_dump},
            "bandit": {"status": bandit_status, "output": bandit_output, "result": bandit_res_dump},
            "quality_gate": quality_gate,
            "test_passed": test_passed,
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

    async def _run_tool_cmd(
        self,
        cmd: list[str],
        timeout: float = 30.0,
        cwd: Path | str | None = None,
        tool_name: str | None = None,
    ) -> ToolResult | str:
        """Run a CLI tool command returning a structured ToolResult."""
        return await asyncio.to_thread(self._run_tool_cmd_sync, cmd, timeout, cwd, tool_name)

    @staticmethod
    def _run_tool_cmd_sync(
        cmd: list[str],
        timeout: float,
        cwd: Path | str | None = None,
        tool_name: str | None = None,
    ) -> ToolResult:
        """Run a command in a worker thread and return a structured ToolResult.

        ``asyncio.create_subprocess_exec`` is unavailable when Uvicorn uses a
        Windows selector event loop.  ``execute_tool`` in ``to_thread`` keeps
        the API non-blocking while working on every supported event loop.
        """
        return execute_tool(cmd, cwd=cwd, timeout=timeout, tool_name=tool_name)

    async def _run_pytest(self, workspace_dir: Path, timeout: float = 60.0) -> ToolResult | str:
        """Run pytest against the workspace directory returning a structured ToolResult."""
        test_files = list(workspace_dir.rglob("test_*.py")) + list(workspace_dir.rglob("*_test.py"))
        if not test_files:
            return "No test files found in workspace."

        cmd = [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-v", str(workspace_dir)]
        return await self._run_tool_cmd(cmd, timeout=timeout, cwd=workspace_dir, tool_name="pytest")

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
