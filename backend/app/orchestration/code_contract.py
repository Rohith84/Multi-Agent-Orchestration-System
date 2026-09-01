"""
Deterministic Code Contract Validator.

Enforces structural, syntactic, and completeness invariants on generated code files before Quality Gate execution.

Validates:
- Planned manifest files exist
- Files are not empty, whitespace-only, or comment-only
- Python files are syntactically valid (ast.parse)
- Concrete functions do not contain only 'pass', raise NotImplementedError, or standalone '...'
- Legitimate abstract methods (@abstractmethod) and Protocol methods are preserved
- Placeholder comments (# implementation here, # TODO: implement, etc.) are detected
- Path traversal attempts outside workspace are rejected
"""

from __future__ import annotations

import ast
import os
import re
from enum import Enum
from pathlib import Path
from typing import Any, Sequence

from pydantic import BaseModel, ConfigDict, Field

PLACEHOLDER_REGEX = re.compile(
    r"#\s*(implementation here|TODO:\s*implement|add more here|\.\.\.\s*rest of code|code here)",
    re.IGNORECASE,
)


class CodeContractStatus(str, Enum):
    """Deterministic status of CodeContract validation."""

    VALID = "VALID"
    CONTRACT_FAILURE = "CONTRACT_FAILURE"


class CodeContractError(BaseModel):
    """Structured code contract validation error."""

    file: str = Field(..., description="Offending relative file path")
    message: str = Field(..., description="Detailed failure explanation")
    line: int | None = Field(default=None, description="Line number of violation if available")
    rule: str = Field(..., description="Contract rule identifier")


class CodeContractResult(BaseModel):
    """Result returned by CodeContractValidator."""

    status: CodeContractStatus = Field(..., description="VALID or CONTRACT_FAILURE")
    is_valid: bool = Field(..., description="True if VALID, False if CONTRACT_FAILURE")
    errors: list[CodeContractError] = Field(default_factory=list, description="List of violations")
    summary: str = Field(..., description="Human readable result summary")

    model_config = ConfigDict(use_enum_values=True)


class CodeContractValidator:
    """
    Deterministic Validator for checking generated code files before Quality Gate execution.

    Read-only: does not modify, repair, or delete any files.
    """

    @classmethod
    def validate(
        cls,
        workspace_dir: Path,
        planned_files: list[str] | None = None,
    ) -> CodeContractResult:
        """
        Validate all generated files in the workspace directory.

        Args:
            workspace_dir: Absolute path to the sandbox workspace.
            planned_files: Optional list of relative file paths expected from Planner's manifest.

        Returns:
            CodeContractResult containing validation status and specific violations.
        """
        errors: list[CodeContractError] = []

        if not workspace_dir.exists():
            errors.append(
                CodeContractError(
                    file=str(workspace_dir),
                    message=f"Workspace directory does not exist: {workspace_dir}",
                    line=None,
                    rule="MISSING_WORKSPACE",
                )
            )
            return CodeContractResult(
                status=CodeContractStatus.CONTRACT_FAILURE,
                is_valid=False,
                errors=errors,
                summary=f"Workspace directory does not exist: {workspace_dir}",
            )

        resolved_workspace = workspace_dir.resolve()

        # 1. Validate manifest file presence
        if planned_files:
            for planned in planned_files:
                clean_rel = planned.strip().lstrip("/\\")
                try:
                    target_path = cls._resolve_safe_path(resolved_workspace, clean_rel)
                    if not target_path.exists():
                        errors.append(
                            CodeContractError(
                                file=clean_rel,
                                message=f"Planned manifest file is missing: '{clean_rel}'",
                                line=None,
                                rule="MISSING_MANIFEST_FILE",
                            )
                        )
                except ValueError as e:
                    errors.append(
                        CodeContractError(
                            file=clean_rel,
                            message=str(e),
                            line=None,
                            rule="PATH_TRAVERSAL_DENIED",
                        )
                    )

        # 2. Collect all files in workspace to validate
        files_to_check: list[tuple[str, Path]] = []

        if planned_files:
            for planned in planned_files:
                clean_rel = planned.strip().lstrip("/\\")
                try:
                    target_path = cls._resolve_safe_path(resolved_workspace, clean_rel)
                    if target_path.exists() and target_path.is_file():
                        files_to_check.append((clean_rel, target_path))
                except ValueError:
                    pass
        else:
            for p in resolved_workspace.rglob("*"):
                if p.is_file() and not cls._is_ignored_path(p, resolved_workspace):
                    rel = str(p.relative_to(resolved_workspace)).replace("\\", "/")
                    files_to_check.append((rel, p))

        # Deduplicate files
        seen_paths: set[str] = set()
        unique_files: list[tuple[str, Path]] = []
        for rel, path in files_to_check:
            if rel not in seen_paths:
                seen_paths.add(rel)
                unique_files.append((rel, path))

        # 3. Validate content of each file
        for rel_path, abs_path in unique_files:
            file_errors = cls._validate_file(rel_path, abs_path)
            errors.extend(file_errors)

        is_valid = len(errors) == 0
        status = CodeContractStatus.VALID if is_valid else CodeContractStatus.CONTRACT_FAILURE

        if is_valid:
            summary = f"CodeContract VALID: All checks passed across {len(unique_files)} files."
        else:
            summary = f"CodeContract CONTRACT_FAILURE: {len(errors)} violation(s) detected across {len(unique_files)} files."

        return CodeContractResult(
            status=status,
            is_valid=is_valid,
            errors=errors,
            summary=summary,
        )

    @classmethod
    def _validate_file(cls, rel_path: str, abs_path: Path) -> list[CodeContractError]:
        """Validate an individual file for contract rules."""
        errors: list[CodeContractError] = []

        try:
            raw_bytes = abs_path.read_bytes()
        except Exception as exc:
            errors.append(
                CodeContractError(
                    file=rel_path,
                    message=f"Failed reading file: {exc}",
                    line=None,
                    rule="UNREADABLE_FILE",
                )
            )
            return errors

        # Rule 2: Empty file check (0 bytes)
        if len(raw_bytes) == 0:
            errors.append(
                CodeContractError(
                    file=rel_path,
                    message="File is completely empty (0 bytes)",
                    line=1,
                    rule="EMPTY_FILE",
                )
            )
            return errors

        content = raw_bytes.decode("utf-8", errors="replace")

        # Rule 3 & 8: Whitespace-only or Comment-only File Check
        if rel_path.endswith(".py"):
            lines = content.splitlines()
            code_lines = [
                line.strip()
                for line in lines
                if line.strip() and not line.strip().startswith("#")
            ]
            if not code_lines:
                errors.append(
                    CodeContractError(
                        file=rel_path,
                        message="File contains only comments or whitespace",
                        line=1,
                        rule="COMMENT_OR_WHITESPACE_ONLY",
                    )
                )
                return errors

        # Rule 6: Placeholder Comment Detection
        for line_idx, line in enumerate(content.splitlines(), start=1):
            if PLACEHOLDER_REGEX.search(line):
                errors.append(
                    CodeContractError(
                        file=rel_path,
                        message=f"Placeholder comment detected: '{line.strip()}'",
                        line=line_idx,
                        rule="PLACEHOLDER_COMMENT",
                    )
                )

        # Python-specific AST and structure checks
        if rel_path.endswith(".py"):
            # Rule 4: AST parsing & Syntax Error detection
            try:
                tree = ast.parse(content, filename=rel_path)
            except SyntaxError as e:
                errors.append(
                    CodeContractError(
                        file=rel_path,
                        message=f"Syntax error: {e.msg}",
                        line=e.lineno,
                        rule="SYNTAX_ERROR",
                    )
                )
                return errors
            except Exception as e:
                errors.append(
                    CodeContractError(
                        file=rel_path,
                        message=f"AST parse failure: {e}",
                        line=None,
                        rule="AST_PARSE_FAILURE",
                    )
                )
                return errors

            # Rule 4, 5, 6, 7: AST Function Body inspection
            ast_errors = cls._check_ast_functions(tree, rel_path)
            errors.extend(ast_errors)

        return errors

    @classmethod
    def _check_ast_functions(cls, tree: ast.AST, rel_path: str) -> list[CodeContractError]:
        """Inspect AST function definitions for incomplete concrete implementation stubs."""
        errors: list[CodeContractError] = []

        class FunctionVisitor(ast.NodeVisitor):
            def __init__(self, validator_cls: type[CodeContractValidator]):
                self.validator_cls = validator_cls
                self.class_stack: list[ast.ClassDef] = []

            def visit_ClassDef(self, node: ast.ClassDef):
                self.class_stack.append(node)
                self.generic_visit(node)
                self.class_stack.pop()

            def visit_FunctionDef(self, node: ast.FunctionDef):
                self._check_func(node)
                self.generic_visit(node)

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
                self._check_func(node)
                self.generic_visit(node)

            def _check_func(self, node: ast.FunctionDef | ast.AsyncFunctionDef):
                parent_class = self.class_stack[-1] if self.class_stack else None
                if self.validator_cls._is_abstract_function(node, parent_class):
                    return

                stmts = node.body
                # Filter out leading docstring if present
                if len(stmts) > 1 and self.validator_cls._is_docstring_stmt(stmts[0]):
                    stmts = stmts[1:]

                if len(stmts) == 1:
                    stmt = stmts[0]
                    # Check pass statement
                    if isinstance(stmt, ast.Pass):
                        errors.append(
                            CodeContractError(
                                file=rel_path,
                                message=f"Concrete function '{node.name}' contains only 'pass'",
                                line=node.lineno,
                                rule="CONCRETE_FUNCTION_PASS",
                            )
                        )
                    # Check raise NotImplementedError
                    elif isinstance(stmt, ast.Raise):
                        if self.validator_cls._is_not_implemented_error(stmt.exc):
                            errors.append(
                                CodeContractError(
                                    file=rel_path,
                                    message=f"Concrete function '{node.name}' raises NotImplementedError",
                                    line=node.lineno,
                                    rule="CONCRETE_FUNCTION_NOT_IMPLEMENTED",
                                )
                            )
                    # Check standalone Ellipsis (...)
                    elif (
                        isinstance(stmt, ast.Expr)
                        and isinstance(stmt.value, ast.Constant)
                        and stmt.value.value is Ellipsis
                    ):
                        errors.append(
                            CodeContractError(
                                file=rel_path,
                                message=f"Concrete function '{node.name}' contains placeholder ellipsis '...'",
                                line=node.lineno,
                                rule="CONCRETE_FUNCTION_ELLIPSIS",
                            )
                        )

        visitor = FunctionVisitor(cls)
        visitor.visit(tree)
        return errors

    @classmethod
    def _is_abstract_function(
        cls,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        parent_class: ast.ClassDef | None,
    ) -> bool:
        """Check if function is a legitimate abstract method or Protocol method."""
        # 1. Check decorators on function
        for dec in node.decorator_list:
            if isinstance(dec, ast.Name) and dec.id in ("abstractmethod", "abstractclassmethod", "abstractstaticmethod"):
                return True
            if isinstance(dec, ast.Attribute) and dec.attr in ("abstractmethod", "abstractclassmethod", "abstractstaticmethod"):
                return True
            if isinstance(dec, ast.Name) and dec.id in ("overload", "override"):
                return True
            if isinstance(dec, ast.Attribute) and dec.attr in ("overload", "override"):
                return True

        # 2. Check parent class bases for Protocol or ABC
        if parent_class:
            for base in parent_class.bases:
                base_name = ""
                if isinstance(base, ast.Name):
                    base_name = base.id
                elif isinstance(base, ast.Attribute):
                    base_name = base.attr

                if base_name in ("Protocol", "TypedDict"):
                    return True

        return False

    @staticmethod
    def _is_docstring_stmt(stmt: ast.stmt) -> bool:
        """Return True if statement is a docstring string expression."""
        return (
            isinstance(stmt, ast.Expr)
            and isinstance(stmt.value, ast.Constant)
            and isinstance(stmt.value.value, str)
        )

    @staticmethod
    def _is_not_implemented_error(exc: ast.expr | None) -> bool:
        """Return True if exception expression is NotImplementedError or NotImplementedError(...)."""
        if exc is None:
            return False
        if isinstance(exc, ast.Name) and exc.id == "NotImplementedError":
            return True
        if isinstance(exc, ast.Call):
            if isinstance(exc.func, ast.Name) and exc.func.id == "NotImplementedError":
                return True
            if isinstance(exc.func, ast.Attribute) and exc.func.attr == "NotImplementedError":
                return True
        return False

    @staticmethod
    def _resolve_safe_path(workspace_dir: Path, relative_path: str) -> Path:
        """Resolve path safely inside workspace directory to prevent path traversal."""
        clean_rel = relative_path.lstrip("/\\")
        resolved_workspace = workspace_dir.resolve()
        target_path = (resolved_workspace / clean_rel).resolve()
        if not str(target_path).startswith(str(resolved_workspace)):
            raise ValueError(f"Path traversal denied outside workspace: {relative_path}")
        return target_path

    @staticmethod
    def _is_ignored_path(path: Path, workspace_dir: Path) -> bool:
        """Return True if path should be ignored during workspace validation."""
        rel_parts = path.relative_to(workspace_dir).parts
        ignored_names = {"__pycache__", ".pytest_cache", ".git", ".venv", "venv", ".idea", ".vscode"}
        return any(part in ignored_names for part in rel_parts)
