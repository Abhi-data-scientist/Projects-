"""
SQL validation layer.
LLM-generated SQL is NEVER executed directly — it always passes
through here first. Simple rule-based validation, no parser library.
"""

import re

ALLOWED_TABLES = {"customers", "products", "orders", "order_items"}

BLOCKED_KEYWORDS = [
    "insert", "update", "delete", "drop", "alter", "truncate",
    "create", "grant", "revoke", "replace", "exec", "execute",
    "call", "merge", "into outfile", "load_file",
]

BLOCKED_SCHEMAS = ["information_schema", "mysql", "performance_schema", "sys"]


class SQLValidationError(Exception):
    pass


def _strip_sql_comments(sql: str) -> str:
    sql = re.sub(r"--.*?$", "", sql, flags=re.MULTILINE)
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    return sql


def validate_sql(sql: str) -> str:
    """
    Validates an LLM-generated SQL string.
    Raises SQLValidationError if unsafe.
    Returns the cleaned, validated SQL on success.
    """
    if not sql or not sql.strip():
        raise SQLValidationError("Empty SQL query.")

    cleaned = _strip_sql_comments(sql).strip()
    # Remove a single trailing semicolon if present
    cleaned = cleaned.rstrip(";").strip()

    lowered = cleaned.lower()

    # Must be a SELECT statement
    if not lowered.startswith("select"):
        raise SQLValidationError("Only SELECT queries are allowed.")

    # Reject multiple statements / stacked queries
    if ";" in cleaned:
        raise SQLValidationError("Multiple SQL statements are not allowed.")

    # Reject blocked keywords (as whole words)
    for keyword in BLOCKED_KEYWORDS:
        if re.search(rf"\b{re.escape(keyword)}\b", lowered):
            raise SQLValidationError(f"Blocked SQL keyword detected: {keyword}")

    # Reject UNION-based attacks
    if re.search(r"\bunion\b", lowered):
        raise SQLValidationError("UNION queries are not allowed.")

    # Reject system schema access
    for schema in BLOCKED_SCHEMAS:
        if schema in lowered:
            raise SQLValidationError(f"Access to '{schema}' is not allowed.")

    # Ensure only whitelisted tables are referenced
    referenced_tables = set(re.findall(r"\bfrom\s+([a-zA-Z_][a-zA-Z0-9_]*)", lowered))
    referenced_tables |= set(re.findall(r"\bjoin\s+([a-zA-Z_][a-zA-Z0-9_]*)", lowered))

    if not referenced_tables:
        raise SQLValidationError("Could not determine target table(s).")

    disallowed = referenced_tables - ALLOWED_TABLES
    if disallowed:
        raise SQLValidationError(f"Query references disallowed table(s): {', '.join(disallowed)}")

    return cleaned
