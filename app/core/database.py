"""
Plain MySQL access using mysql-connector-python.
No SQLAlchemy, no ORM, no Alembic — just raw SQL.
"""

import logging
import mysql.connector
from mysql.connector import Error as MySQLError

from core.config import settings

logger = logging.getLogger("database")


def get_connection():
    """Open a new MySQL connection."""
    return mysql.connector.connect(
        host=settings.MYSQL_HOST,
        port=settings.MYSQL_PORT,
        user=settings.MYSQL_USER,
        password=settings.MYSQL_PASSWORD,
        database=settings.MYSQL_DATABASE,
    )


def execute_query(query: str, params: tuple | None = None) -> int:
    """
    Run a write query (INSERT/UPDATE/DELETE) used by internal services.
    Not exposed to user SQL.
    Returns number of affected rows.
    """
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params or ())
        conn.commit()
        return cursor.rowcount
    except MySQLError as e:
        if conn:
            conn.rollback()
        logger.error(f"execute_query failed: {e}")
        raise
    finally:
        close_connection(conn, cursor)


def execute_insert(query: str, params: tuple | None = None) -> int:
    """
    Run an INSERT query and return the last inserted row id.
    """
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params or ())
        conn.commit()
        return cursor.lastrowid
    except MySQLError as e:
        if conn:
            conn.rollback()
        logger.error(f"execute_insert failed: {e}")
        raise
    finally:
        close_connection(conn, cursor)


def execute_select(query: str, params: tuple | None = None) -> list[dict]:
    """
    Run a read-only SELECT query and return rows as a list of dicts.
    This is the only path used for LLM-generated SQL.
    """
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params or ())
        rows = cursor.fetchmany(settings.MAX_SQL_ROWS)
        return rows
    except MySQLError as e:
        logger.error(f"execute_select failed: {e}")
        raise
    finally:
        close_connection(conn, cursor)


def close_connection(conn=None, cursor=None):
    """Close cursor and connection safely."""
    try:
        if cursor is not None:
            cursor.close()
    except Exception:
        pass
    try:
        if conn is not None and conn.is_connected():
            conn.close()
    except Exception:
        pass


def check_connection() -> bool:
    """Used by /health to verify DB is reachable."""
    try:
        conn = get_connection()
        alive = conn.is_connected()
        close_connection(conn)
        return alive
    except Exception as e:
        logger.error(f"DB health check failed: {e}")
        return False
