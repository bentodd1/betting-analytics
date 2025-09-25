"""
Database connection utilities for betting analytics platform
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
import logging
from typing import Optional, Dict, Any, List

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseConnection:
    """Manages PostgreSQL database connections and operations"""

    def __init__(self, connection_string: Optional[str] = None):
        """
        Initialize database connection

        Args:
            connection_string: PostgreSQL connection string. If None, uses environment variables.
        """
        if connection_string:
            self.connection_string = connection_string
        else:
            # Build connection string from environment variables
            host = os.getenv('DB_HOST', 'localhost')
            port = os.getenv('DB_PORT', '5432')
            database = os.getenv('DB_NAME', 'betting_analytics')
            user = os.getenv('DB_USER', 'postgres')
            password = os.getenv('DB_PASSWORD', 'password')

            self.connection_string = f"host={host} port={port} database={database} user={user} password={password}"

    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections

        Yields:
            psycopg2 connection object
        """
        conn = None
        try:
            conn = psycopg2.connect(self.connection_string)
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    @contextmanager
    def get_cursor(self, dict_cursor=True):
        """
        Context manager for database cursors

        Args:
            dict_cursor: If True, returns dict-like cursor results

        Yields:
            psycopg2 cursor object
        """
        with self.get_connection() as conn:
            cursor_factory = RealDictCursor if dict_cursor else None
            cursor = conn.cursor(cursor_factory=cursor_factory)
            try:
                yield cursor
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error(f"Cursor error: {e}")
                raise
            finally:
                cursor.close()

    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[Any, Any]]:
        """
        Execute a SELECT query and return results

        Args:
            query: SQL query string
            params: Query parameters tuple

        Returns:
            List of dictionaries representing rows
        """
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()

    def execute_insert(self, query: str, params: Optional[tuple] = None) -> Optional[int]:
        """
        Execute an INSERT query and return the inserted row ID

        Args:
            query: SQL INSERT query string
            params: Query parameters tuple

        Returns:
            Inserted row ID if available
        """
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            try:
                return cursor.fetchone()[0] if cursor.rowcount > 0 else None
            except:
                return cursor.rowcount

    def execute_many(self, query: str, params_list: List[tuple]) -> int:
        """
        Execute query with multiple parameter sets (batch insert)

        Args:
            query: SQL query string
            params_list: List of parameter tuples

        Returns:
            Number of affected rows
        """
        with self.get_cursor() as cursor:
            cursor.executemany(query, params_list)
            return cursor.rowcount

    def test_connection(self) -> bool:
        """
        Test database connection

        Returns:
            True if connection successful, False otherwise
        """
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                logger.info("Database connection successful")
                return result[0] == 1
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False

    def get_table_info(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Get information about a table's columns

        Args:
            table_name: Name of the table

        Returns:
            List of column information dictionaries
        """
        query = """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = %s
        ORDER BY ordinal_position
        """
        return self.execute_query(query, (table_name,))

    def get_table_count(self, table_name: str) -> int:
        """
        Get row count for a table

        Args:
            table_name: Name of the table

        Returns:
            Number of rows in the table
        """
        query = f"SELECT COUNT(*) FROM {table_name}"
        result = self.execute_query(query)
        return result[0]['count'] if result else 0


# Convenience functions for common operations
def get_db_connection() -> DatabaseConnection:
    """Get a database connection instance"""
    return DatabaseConnection()

def init_database():
    """Initialize database with schema"""
    db = get_db_connection()

    # Read and execute schema file
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')

    if not os.path.exists(schema_path):
        raise FileNotFoundError(f"Schema file not found: {schema_path}")

    with open(schema_path, 'r') as f:
        schema_sql = f.read()

    try:
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(schema_sql)
            logger.info("Database schema initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database schema: {e}")
        return False

def get_database_status() -> Dict[str, Any]:
    """
    Get database status and table information

    Returns:
        Dictionary with database status information
    """
    db = get_db_connection()

    status = {
        'connection': db.test_connection(),
        'tables': {}
    }

    if status['connection']:
        # Get table counts
        tables = ['sports', 'teams', 'games', 'bookmakers', 'moneylines', 'spreads', 'totals', 'bet_outcomes']

        for table in tables:
            try:
                count = db.get_table_count(table)
                status['tables'][table] = {
                    'count': count,
                    'exists': True
                }
            except Exception as e:
                status['tables'][table] = {
                    'count': 0,
                    'exists': False,
                    'error': str(e)
                }

    return status


if __name__ == "__main__":
    # Test the database connection
    db = get_db_connection()

    print("Testing database connection...")
    if db.test_connection():
        print("✅ Database connection successful!")

        print("\nGetting database status...")
        status = get_database_status()
        print(f"Connection: {status['connection']}")

        print("\nTable information:")
        for table_name, info in status['tables'].items():
            if info['exists']:
                print(f"  {table_name}: {info['count']} rows")
            else:
                print(f"  {table_name}: ❌ Not found")

    else:
        print("❌ Database connection failed!")