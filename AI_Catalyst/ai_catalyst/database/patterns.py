"""
Database Patterns - Common async database patterns and utilities

Provides reusable patterns for database operations.
"""

import asyncio
from typing import Dict, Any, List, Optional, Callable
from contextlib import asynccontextmanager
import logging

logger = logging.getLogger(__name__)


class AsyncConnectionPool:
    """Async connection pool wrapper with common patterns"""
    
    def __init__(self, db_manager):
        """
        Initialize with database manager
        
        Args:
            db_manager: DatabaseManager instance
        """
        self.db_manager = db_manager
    
    @asynccontextmanager
    async def transaction(self):
        """
        Database transaction context manager
        
        Usage:
            async with pool.transaction() as conn:
                await conn.execute("INSERT ...")
                await conn.execute("UPDATE ...")
                # Automatically commits on success, rolls back on exception
        """
        async with self.db_manager.get_connection() as conn:
            async with conn.transaction():
                yield conn
    
    async def execute_batch(self, operations: List[Dict[str, Any]]) -> List[Any]:
        """
        Execute multiple operations in a transaction
        
        Args:
            operations: List of operation dicts with 'query' and 'args' keys
            
        Returns:
            List of operation results
        """
        results = []
        
        async with self.transaction() as conn:
            for op in operations:
                query = op['query']
                args = op.get('args', [])
                
                if query.strip().upper().startswith('SELECT'):
                    result = await conn.fetch(query, *args)
                    results.append([dict(row) for row in result])
                else:
                    result = await conn.execute(query, *args)
                    results.append(result)
        
        return results
    
    async def bulk_insert(self, table: str, records: List[Dict[str, Any]], 
                         batch_size: int = 1000) -> int:
        """
        Bulk insert records with batching
        
        Args:
            table: Table name
            records: List of record dicts
            batch_size: Number of records per batch
            
        Returns:
            Total number of records inserted
        """
        if not records:
            return 0
        
        # Get column names from first record
        columns = list(records[0].keys())
        placeholders = ', '.join([f'${i+1}' for i in range(len(columns))])
        query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
        
        total_inserted = 0
        
        # Process in batches
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            
            async with self.transaction() as conn:
                for record in batch:
                    values = [record[col] for col in columns]
                    await conn.execute(query, *values)
                    total_inserted += 1
        
        return total_inserted
    
    async def upsert(self, table: str, record: Dict[str, Any], 
                    conflict_columns: List[str]) -> str:
        """
        Insert or update record on conflict
        
        Args:
            table: Table name
            record: Record data
            conflict_columns: Columns that define uniqueness
            
        Returns:
            Operation result
        """
        columns = list(record.keys())
        values = list(record.values())
        
        # Build INSERT part
        placeholders = ', '.join([f'${i+1}' for i in range(len(columns))])
        insert_part = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
        
        # Build ON CONFLICT part
        conflict_part = f"ON CONFLICT ({', '.join(conflict_columns)}) DO UPDATE SET"
        update_assignments = [f"{col} = EXCLUDED.{col}" for col in columns if col not in conflict_columns]
        update_part = ', '.join(update_assignments)
        
        query = f"{insert_part} {conflict_part} {update_part}"
        
        return await self.db_manager.execute(query, *values)
    
    async def paginate(self, base_query: str, args: List[Any], 
                      page_size: int = 100, offset: int = 0) -> Dict[str, Any]:
        """
        Paginate query results
        
        Args:
            base_query: Base SELECT query (without LIMIT/OFFSET)
            args: Query arguments
            page_size: Number of records per page
            offset: Starting offset
            
        Returns:
            Dict with 'data', 'total', 'page_size', 'offset' keys
        """
        # Get total count
        count_query = f"SELECT COUNT(*) as total FROM ({base_query}) as subquery"
        count_result = await self.db_manager.fetchrow(count_query, *args)
        total = count_result['total'] if count_result else 0
        
        # Get paginated data
        paginated_query = f"{base_query} LIMIT {page_size} OFFSET {offset}"
        data = await self.db_manager.fetchall(paginated_query, *args)
        
        return {
            'data': data,
            'total': total,
            'page_size': page_size,
            'offset': offset,
            'has_more': offset + page_size < total
        }
    
    async def execute_with_retry(self, operation: Callable, max_retries: int = 3, 
                               delay: float = 1.0) -> Any:
        """
        Execute database operation with retry logic
        
        Args:
            operation: Async function to execute
            max_retries: Maximum number of retries
            delay: Delay between retries in seconds
            
        Returns:
            Operation result
        """
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                return await operation()
            except Exception as e:
                last_exception = e
                if attempt < max_retries:
                    logger.warning(f"Database operation failed (attempt {attempt + 1}/{max_retries + 1}): {e}")
                    await asyncio.sleep(delay * (2 ** attempt))  # Exponential backoff
                else:
                    logger.error(f"Database operation failed after {max_retries + 1} attempts: {e}")
        
        raise last_exception