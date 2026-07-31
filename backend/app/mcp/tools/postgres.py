"""
PostgreSQL MCP Tool.

Provides read-only database access:
- Execute SELECT queries
- List tables
- Describe table schema

Blocks all write/destructive operations.
"""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.database import async_session_factory
from app.mcp.registry import ToolRegistry, ToolDefinition

logger = get_logger(__name__)

# Dangerous SQL patterns — case-insensitive
_BLOCKED_PATTERNS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE|EXEC|EXECUTE)\b",
    re.IGNORECASE,
)


def _validate_sql(sql: str) -> None:
    """
    Validate that a SQL query is read-only.

    Raises PermissionError for any write/destructive operations.
    """
    stripped = sql.strip().rstrip(";")

    if _BLOCKED_PATTERNS.search(stripped):
        raise PermissionError(
            "Write operations are not allowed. Only SELECT queries are permitted. "
            "Blocked keywords: INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE, GRANT, REVOKE, EXEC."
        )

    # Must start with SELECT, WITH, SHOW, or EXPLAIN
    upper = stripped.upper().lstrip()
    if not any(upper.startswith(kw) for kw in ("SELECT", "WITH", "SHOW", "EXPLAIN")):
        raise PermissionError(
            "Only SELECT, WITH, SHOW, and EXPLAIN queries are allowed."
        )


async def execute_query(sql: str) -> dict[str, Any]:
    """
    Execute a read-only SQL query against the PostgreSQL database.

    Args:
        sql: SQL query string. Must be a SELECT query.

    Returns:
        Dict with columns, rows, and row count.
    """
    _validate_sql(sql)

    async with async_session_factory() as session:
        try:
            result = await session.execute(text(sql))
            columns = list(result.keys()) if result.returns_rows else []
            rows = [dict(zip(columns, row)) for row in result.fetchall()] if result.returns_rows else []

            # Limit to 200 rows
            truncated = len(rows) > 200
            rows = rows[:200]

            # Convert non-serializable types to strings
            for row in rows:
                for key, value in row.items():
                    if not isinstance(value, (str, int, float, bool, type(None))):
                        row[key] = str(value)

            return {
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
                "truncated": truncated,
            }
        except Exception as e:
            raise ValueError(f"SQL execution error: {str(e)}")


async def list_tables() -> dict[str, Any]:
    """
    List all tables in the public schema.

    Returns:
        Dict with list of table names.
    """
    sql = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name;
    """
    async with async_session_factory() as session:
        try:
            result = await session.execute(text(sql))
            tables = [row[0] for row in result.fetchall()]
            return {"tables": tables, "count": len(tables)}
        except Exception as e:
            raise ValueError(f"Failed to list tables: {str(e)}")


async def describe_table(table_name: str) -> dict[str, Any]:
    """
    Describe the schema of a specific table.

    Args:
        table_name: Name of the table to describe.

    Returns:
        Dict with column definitions.
    """
    # Sanitize table name — only allow alphanumeric and underscores
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", table_name):
        raise ValueError(f"Invalid table name: {table_name}")

    sql = """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = :table_name
        ORDER BY ordinal_position;
    """
    async with async_session_factory() as session:
        try:
            result = await session.execute(text(sql), {"table_name": table_name})
            columns = []
            for row in result.fetchall():
                columns.append({
                    "column_name": row[0],
                    "data_type": row[1],
                    "is_nullable": row[2],
                    "column_default": str(row[3]) if row[3] else None,
                })

            if not columns:
                raise ValueError(f"Table '{table_name}' not found.")

            return {"table_name": table_name, "columns": columns, "column_count": len(columns)}
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Failed to describe table: {str(e)}")


def register_postgres_tools() -> None:
    """Register all PostgreSQL tools with the MCP registry."""
    registry = ToolRegistry.instance()

    registry.register(ToolDefinition(
        name="postgres.execute_query",
        description="Execute a read-only SQL query against the PostgreSQL database. Only SELECT queries allowed.",
        category="database",
        parameters={
            "properties": {
                "sql": {
                    "type": "string",
                    "description": "SQL SELECT query to execute.",
                },
            },
            "required": ["sql"],
        },
        handler=execute_query,
    ))

    registry.register(ToolDefinition(
        name="postgres.list_tables",
        description="List all tables in the PostgreSQL public schema.",
        category="database",
        parameters={
            "properties": {},
            "required": [],
        },
        handler=list_tables,
    ))

    registry.register(ToolDefinition(
        name="postgres.describe_table",
        description="Describe the schema of a specific database table.",
        category="database",
        parameters={
            "properties": {
                "table_name": {
                    "type": "string",
                    "description": "Name of the table to describe.",
                },
            },
            "required": ["table_name"],
        },
        handler=describe_table,
    ))

    logger.info("PostgreSQL tools registered")
