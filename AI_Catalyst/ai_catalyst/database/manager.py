"""
Database Manager - Async PostgreSQL patterns and utilities

Provides connection pooling, common database operations, and data access patterns.
"""

import asyncio
from typing import Optional, Dict, Any, List, Union
from contextlib import asynccontextmanager
from datetime import datetime
import uuid
import json
import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Async PostgreSQL database manager with connection pooling"""
    
    def __init__(self, db_config: Union[str, Dict[str, Any]]):
        """
        Initialize database manager
        
        Args:
            db_config: Database URL string or config dict with keys:
                      host, port, database, user, password
        """
        if isinstance(db_config, str):
            self.db_url = db_config
            self.db_config = None
        else:
            self.db_config = db_config
            self.db_url = self._build_url_from_config(db_config)
        
        self.pool = None
        self._initialized = False
    
    def _build_url_from_config(self, config: Dict[str, Any]) -> str:
        """Build database URL from config dict"""
        host = config.get('host', 'localhost')
        port = config.get('port', 5432)
        database = config.get('database', 'postgres')
        user = config.get('user', 'postgres')
        password = config.get('password', '')
        
        return f"postgresql://{user}:{password}@{host}:{port}/{database}"
    
    async def initialize(self, min_size: int = 5, max_size: int = 20, command_timeout: int = 60):
        """
        Initialize database connection pool
        
        Args:
            min_size: Minimum pool size
            max_size: Maximum pool size
            command_timeout: Command timeout in seconds
        """
        if self._initialized:
            return
        
        try:
            # Try to import asyncpg
            import asyncpg
            
            self.pool = await asyncpg.create_pool(
                self.db_url,
                min_size=min_size,
                max_size=max_size,
                command_timeout=command_timeout
            )
            self._initialized = True
            logger.info("Database connection pool initialized")
        except ImportError:
            logger.error("asyncpg not available, database functionality disabled")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise
    
    @asynccontextmanager
    async def get_connection(self):
        """
        Get database connection from pool
        
        Usage:
            async with db_manager.get_connection() as conn:
                result = await conn.fetchrow("SELECT * FROM table")
        """
        if not self._initialized or not self.pool:
            raise RuntimeError("Database not initialized")
        
        async with self.pool.acquire() as conn:
            yield conn
    
    async def execute(self, query: str, *args) -> str:
        """
        Execute a query that doesn't return data
        
        Args:
            query: SQL query
            *args: Query parameters
            
        Returns:
            Query execution status
        """
        async with self.get_connection() as conn:
            return await conn.execute(query, *args)
    
    async def fetchrow(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """
        Fetch single row
        
        Args:
            query: SQL query
            *args: Query parameters
            
        Returns:
            Single row as dict or None
        """
        async with self.get_connection() as conn:
            row = await conn.fetchrow(query, *args)
            return dict(row) if row else None
    
    async def fetchall(self, query: str, *args) -> List[Dict[str, Any]]:
        """
        Fetch all rows
        
        Args:
            query: SQL query
            *args: Query parameters
            
        Returns:
            List of rows as dicts
        """
        async with self.get_connection() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform database health check
        
        Returns:
            Health check results
        """
        try:
            result = await self.fetchrow("SELECT version(), now() as current_time")
            return {
                'status': 'healthy',
                'version': result['version'] if result else 'unknown',
                'current_time': result['current_time'] if result else None
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    async def close(self):
        """Close database connections"""
        if self.pool:
            await self.pool.close()
            self._initialized = False
            logger.info("Database connection pool closed")
    
    def is_initialized(self) -> bool:
        """Check if database is initialized"""
        return self._initialized