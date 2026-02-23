import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from typing import Generator
from config import settings


@contextmanager
def get_db_connection() -> Generator:
    """
    Context manager for database connections.
    Automatically handles connection cleanup.
    """
    conn = None
    try:
        conn = psycopg2.connect(settings.database_url)
        yield conn
    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()


def execute_query(query: str, params: tuple = None) -> list:
    """
    Execute a query and return results as a list of dictionaries.

    Args:
        query: SQL query string
        params: Optional tuple of parameters for the query

    Returns:
        List of dictionaries containing query results
    """
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params)
            results = cursor.fetchall()
            return [dict(row) for row in results]


def test_connection() -> bool:
    """
    Test if database connection is working.

    Returns:
        True if connection successful, False otherwise
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                return True
    except Exception:
        return False
