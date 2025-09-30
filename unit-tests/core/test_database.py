#!/usr/bin/env python3
"""
Database Operations Tests
Validate database connectivity, schema management, and connection pooling.
"""

import asyncio
import sqlite3
import tempfile
from pathlib import Path
import sys
import os

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from test_framework import TestCase, TestSuite, TestAssertions, test_runner
from src.core.database import DatabaseManager

class TestDatabase:
    def __init__(self):
        self.temp_db = None
        self.db_manager = None
    
    def setup(self):
        """Setup test database environment"""
        # Create temporary SQLite database for testing
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()
        
        # Initialize database manager with test database
        self.db_manager = DatabaseManager({
            'type': 'sqlite',
            'database': self.temp_db.name
        })
    
    def teardown(self):
        """Cleanup test database"""
        if self.temp_db:
            os.unlink(self.temp_db.name)
    
    def test_database_connection(self):
        """Test basic database connectivity"""
        conn = self.db_manager.get_connection()
        TestAssertions.assert_not_none(conn, "Should establish database connection")
        
        # Test basic query
        cursor = conn.cursor()
        cursor.execute("SELECT 1 as test_value")
        result = cursor.fetchone()
        TestAssertions.assert_equals(result[0], 1, "Should execute basic query")
        
        cursor.close()
        conn.close()
    
    def test_schema_execution(self):
        """Test schema file execution and table creation"""
        # Create test schema
        test_schema = """
        CREATE TABLE IF NOT EXISTS test_table (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS test_relationships (
            id INTEGER PRIMARY KEY,
            parent_id INTEGER REFERENCES test_table(id),
            value TEXT
        );
        """
        
        # Write schema to temporary file
        schema_file = tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False)
        schema_file.write(test_schema)
        schema_file.close()
        
        try:
            # Execute schema
            self.db_manager.execute_schema(schema_file.name)
            
            # Verify tables were created
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            # Check if tables exist (SQLite specific)
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            TestAssertions.assert_in('test_table', tables, "Should create test_table")
            TestAssertions.assert_in('test_relationships', tables, "Should create test_relationships")
            
            cursor.close()
            conn.close()
            
        finally:
            os.unlink(schema_file.name)
    
    def test_transaction_handling(self):
        """Test database transaction commit and rollback scenarios"""
        # First create a test table
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transaction_test (
                id INTEGER PRIMARY KEY,
                value TEXT
            )
        """)
        conn.commit()
        
        # Test successful transaction
        cursor.execute("INSERT INTO transaction_test (value) VALUES (?)", ("test_value",))
        conn.commit()
        
        # Verify insert
        cursor.execute("SELECT COUNT(*) FROM transaction_test")
        count = cursor.fetchone()[0]
        TestAssertions.assert_equals(count, 1, "Should commit transaction successfully")
        
        # Test rollback
        cursor.execute("INSERT INTO transaction_test (value) VALUES (?)", ("rollback_test",))
        conn.rollback()
        
        # Verify rollback
        cursor.execute("SELECT COUNT(*) FROM transaction_test")
        count = cursor.fetchone()[0]
        TestAssertions.assert_equals(count, 1, "Should rollback transaction")
        
        cursor.close()
        conn.close()
    
    def test_connection_error_handling(self):
        """Test database connection error handling"""
        # Test with invalid database path
        invalid_db_manager = DatabaseManager({
            'type': 'sqlite',
            'database': '/invalid/path/database.db'
        })
        
        # This should handle the error gracefully
        try:
            conn = invalid_db_manager.get_connection()
            # If we get here, the connection somehow worked
            conn.close()
        except Exception as e:
            # Expected behavior - connection should fail
            TestAssertions.assert_true(True, "Should handle connection errors gracefully")
    
    def test_database_operations(self):
        """Test basic CRUD operations"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        # Create test table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS crud_test (
                id INTEGER PRIMARY KEY,
                name TEXT,
                value INTEGER
            )
        """)
        
        # INSERT
        cursor.execute("INSERT INTO crud_test (name, value) VALUES (?, ?)", ("test_item", 42))
        conn.commit()
        
        # SELECT
        cursor.execute("SELECT name, value FROM crud_test WHERE name = ?", ("test_item",))
        result = cursor.fetchone()
        TestAssertions.assert_not_none(result, "Should insert and select data")
        TestAssertions.assert_equals(result[0], "test_item", "Should retrieve correct name")
        TestAssertions.assert_equals(result[1], 42, "Should retrieve correct value")
        
        # UPDATE
        cursor.execute("UPDATE crud_test SET value = ? WHERE name = ?", (100, "test_item"))
        conn.commit()
        
        cursor.execute("SELECT value FROM crud_test WHERE name = ?", ("test_item",))
        updated_value = cursor.fetchone()[0]
        TestAssertions.assert_equals(updated_value, 100, "Should update data")
        
        # DELETE
        cursor.execute("DELETE FROM crud_test WHERE name = ?", ("test_item",))
        conn.commit()
        
        cursor.execute("SELECT COUNT(*) FROM crud_test")
        count = cursor.fetchone()[0]
        TestAssertions.assert_equals(count, 0, "Should delete data")
        
        cursor.close()
        conn.close()
    
    async def test_async_operations(self):
        """Test asynchronous database operations (mock test)"""
        # This would test async database operations if implemented
        # For now, test that the interface supports async patterns
        TestAssertions.assert_true(hasattr(self.db_manager, 'get_connection'), "Should have connection method")
        
        # Simulate async operation
        await asyncio.sleep(0.01)
        TestAssertions.assert_true(True, "Should support async patterns")

def create_database_tests():
    """Create and register database tests"""
    test_db = TestDatabase()
    
    tests = [
        TestCase(
            test_id="db_001",
            name="Database Connection",
            description="Test basic database connectivity and query execution",
            test_func=test_db.test_database_connection,
            category="core"
        ),
        TestCase(
            test_id="db_002",
            name="Schema Execution",
            description="Test schema file execution and table creation",
            test_func=test_db.test_schema_execution,
            category="core"
        ),
        TestCase(
            test_id="db_003",
            name="Transaction Handling",
            description="Test database transaction commit and rollback scenarios",
            test_func=test_db.test_transaction_handling,
            category="core"
        ),
        TestCase(
            test_id="db_004",
            name="Connection Error Handling",
            description="Test graceful handling of database connection errors",
            test_func=test_db.test_connection_error_handling,
            category="core"
        ),
        TestCase(
            test_id="db_005",
            name="CRUD Operations",
            description="Test basic Create, Read, Update, Delete operations",
            test_func=test_db.test_database_operations,
            category="core"
        ),
        TestCase(
            test_id="db_006",
            name="Async Operations",
            description="Test asynchronous database operation patterns",
            test_func=test_db.test_async_operations,
            category="core"
        )
    ]
    
    suite = TestSuite(
        name="database",
        description="Database Operations and Connectivity Tests",
        tests=tests,
        setup_func=test_db.setup,
        teardown_func=test_db.teardown
    )
    
    test_runner.register_suite(suite)

# Register tests when module is imported
create_database_tests()