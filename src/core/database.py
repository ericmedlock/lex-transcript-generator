"""Database connection and management utilities"""

import asyncio
import asyncpg
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
from datetime import datetime
import uuid
import json


class DatabaseManager:
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.pool: Optional[asyncpg.Pool] = None

    async def initialize(self):
        """Initialize database connection pool"""
        self.pool = await asyncpg.create_pool(
            self.db_url,
            min_size=5,
            max_size=20,
            command_timeout=60
        )

    @asynccontextmanager
    async def get_connection(self):
        """Get database connection from pool"""
        if not self.pool:
            raise RuntimeError("Database not initialized")
        
        async with self.pool.acquire() as conn:
            yield conn

    async def execute_schema(self, schema_file: str):
        """Execute database schema from file"""
        with open(schema_file, 'r') as f:
            schema_sql = f.read()
        
        async with self.get_connection() as conn:
            await conn.execute(schema_sql)

    async def close(self):
        """Close database connections"""
        if self.pool:
            await self.pool.close()


class NodeRegistry:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    async def register_node(self, hostname: str, ip_address: str, node_type: str, 
                          capabilities: Dict[str, Any], hardware_info: Dict[str, Any]) -> str:
        """Register a new node"""
        node_id = str(uuid.uuid4())
        
        async with self.db.get_connection() as conn:
            await conn.execute("""
                INSERT INTO nodes (id, hostname, ip_address, node_type, capabilities, hardware_info, status, last_heartbeat)
                VALUES ($1, $2, $3, $4, $5, $6, 'online', $7)
                ON CONFLICT (hostname) DO UPDATE SET
                    ip_address = EXCLUDED.ip_address,
                    capabilities = EXCLUDED.capabilities,
                    hardware_info = EXCLUDED.hardware_info,
                    status = 'online',
                    last_heartbeat = EXCLUDED.last_heartbeat,
                    updated_at = CURRENT_TIMESTAMP
            """, node_id, hostname, ip_address, node_type, 
                json.dumps(capabilities), json.dumps(hardware_info), datetime.utcnow())
        
        return node_id

    async def update_heartbeat(self, node_id: str, performance_metrics: Dict[str, Any] = None):
        """Update node heartbeat and performance metrics"""
        async with self.db.get_connection() as conn:
            if performance_metrics:
                await conn.execute("""
                    UPDATE nodes SET last_heartbeat = $1, performance_metrics = $2, updated_at = CURRENT_TIMESTAMP
                    WHERE id = $3
                """, datetime.utcnow(), json.dumps(performance_metrics), node_id)
            else:
                await conn.execute("""
                    UPDATE nodes SET last_heartbeat = $1, updated_at = CURRENT_TIMESTAMP
                    WHERE id = $2
                """, datetime.utcnow(), node_id)

    async def get_active_nodes(self, node_type: str = None) -> List[Dict[str, Any]]:
        """Get all active nodes, optionally filtered by type"""
        async with self.db.get_connection() as conn:
            if node_type:
                rows = await conn.fetch("""
                    SELECT * FROM nodes 
                    WHERE status = 'online' AND node_type = $1 
                    AND last_heartbeat > NOW() - INTERVAL '2 minutes'
                """, node_type)
            else:
                rows = await conn.fetch("""
                    SELECT * FROM nodes 
                    WHERE status = 'online' 
                    AND last_heartbeat > NOW() - INTERVAL '2 minutes'
                """)
            
            return [dict(row) for row in rows]

    async def set_node_status(self, node_id: str, status: str):
        """Set node status"""
        async with self.db.get_connection() as conn:
            await conn.execute("""
                UPDATE nodes SET status = $1, updated_at = CURRENT_TIMESTAMP
                WHERE id = $2
            """, status, node_id)


class WorkQueue:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    async def enqueue_job(self, job_type: str, payload: Dict[str, Any], 
                         priority: int = 50) -> str:
        """Add job to work queue"""
        job_id = str(uuid.uuid4())
        
        async with self.db.get_connection() as conn:
            await conn.execute("""
                INSERT INTO work_queue (id, job_type, priority, payload, status)
                VALUES ($1, $2, $3, $4, 'pending')
            """, job_id, job_type, priority, json.dumps(payload))
        
        return job_id

    async def get_next_job(self, node_id: str, job_types: List[str] = None) -> Optional[Dict[str, Any]]:
        """Get next available job for node"""
        async with self.db.get_connection() as conn:
            if job_types:
                job_type_filter = "AND job_type = ANY($2)"
                params = [node_id, job_types]
            else:
                job_type_filter = ""
                params = [node_id]
            
            row = await conn.fetchrow(f"""
                UPDATE work_queue 
                SET status = 'assigned', assigned_node_id = $1, assigned_at = CURRENT_TIMESTAMP
                WHERE id = (
                    SELECT id FROM work_queue 
                    WHERE status = 'pending' {job_type_filter}
                    ORDER BY priority DESC, created_at ASC 
                    LIMIT 1 FOR UPDATE SKIP LOCKED
                )
                RETURNING *
            """, *params)
            
            return dict(row) if row else None

    async def complete_job(self, job_id: str, success: bool = True):
        """Mark job as completed or failed"""
        status = 'completed' if success else 'failed'
        
        async with self.db.get_connection() as conn:
            await conn.execute("""
                UPDATE work_queue 
                SET status = $1, completed_at = CURRENT_TIMESTAMP
                WHERE id = $2
            """, status, job_id)

    async def get_queue_stats(self) -> Dict[str, int]:
        """Get work queue statistics"""
        async with self.db.get_connection() as conn:
            row = await conn.fetchrow("""
                SELECT 
                    COUNT(*) FILTER (WHERE status = 'pending') as pending,
                    COUNT(*) FILTER (WHERE status = 'assigned') as assigned,
                    COUNT(*) FILTER (WHERE status = 'processing') as processing,
                    COUNT(*) FILTER (WHERE status = 'completed') as completed,
                    COUNT(*) FILTER (WHERE status = 'failed') as failed
                FROM work_queue
            """)
            
            return dict(row)


class ConversationStore:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    async def store_conversation(self, scenario_id: str, generated_by_node_id: str,
                               content: Dict[str, Any], metadata: Dict[str, Any] = None,
                               quality_score: float = None, file_path: str = None) -> str:
        """Store generated conversation"""
        conversation_id = str(uuid.uuid4())
        
        async with self.db.get_connection() as conn:
            await conn.execute("""
                INSERT INTO conversations (id, scenario_id, generated_by_node_id, content, metadata, quality_score, file_path)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, conversation_id, scenario_id, generated_by_node_id, 
                json.dumps(content), json.dumps(metadata or {}), quality_score, file_path)
        
        return conversation_id

    async def get_conversations(self, limit: int = 100, min_quality: float = None) -> List[Dict[str, Any]]:
        """Get conversations with optional quality filter"""
        async with self.db.get_connection() as conn:
            if min_quality:
                rows = await conn.fetch("""
                    SELECT * FROM conversations 
                    WHERE quality_score >= $1 
                    ORDER BY created_at DESC 
                    LIMIT $2
                """, min_quality, limit)
            else:
                rows = await conn.fetch("""
                    SELECT * FROM conversations 
                    ORDER BY created_at DESC 
                    LIMIT $1
                """, limit)
            
            return [dict(row) for row in rows]

    async def mark_duplicate(self, conversation_id: str):
        """Mark conversation as duplicate"""
        async with self.db.get_connection() as conn:
            await conn.execute("""
                UPDATE conversations SET is_duplicate = TRUE
                WHERE id = $1
            """, conversation_id)


# Global database manager instance
db_manager: Optional[DatabaseManager] = None


async def init_database(db_url: str, schema_file: str = None):
    """Initialize global database manager"""
    global db_manager
    db_manager = DatabaseManager(db_url)
    await db_manager.initialize()
    
    if schema_file:
        await db_manager.execute_schema(schema_file)