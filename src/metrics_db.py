"""Database interface for performance metrics"""

import asyncio
import asyncpg
import uuid
import json
import socket
from typing import Optional, Dict, Any, List
from datetime import datetime
from .worker_pool import JobResult
from .tuner import WindowStats

class MetricsDB:
    def __init__(self, db_url: str, model_id: str):
        self.db_url = db_url
        self.model_id = model_id
        self.host = socket.gethostname()
        self.pool = None
        self.run_id = None
        
    async def initialize(self):
        """Initialize database connection and create run"""
        self.pool = await asyncpg.create_pool(
            self.db_url,
            min_size=2,
            max_size=5,
            command_timeout=30
        )
        
        # Create new performance run
        async with self.pool.acquire() as conn:
            self.run_id = await conn.fetchval(
                """INSERT INTO perf_runs (model_id, host, notes) 
                   VALUES ($1, $2, $3) RETURNING run_id""",
                self.model_id, self.host, "Automated performance run"
            )
            
    async def close(self):
        """Close database connections and finish run"""
        if self.pool and self.run_id:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "UPDATE perf_runs SET finished_at = NOW() WHERE run_id = $1",
                    self.run_id
                )
        
        if self.pool:
            await self.pool.close()
            
    async def record_job(self, result: JobResult):
        """Record individual job performance"""
        if not self.pool or not self.run_id:
            return
            
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """INSERT INTO perf_jobs 
                       (run_id, started_at, finished_at, latency_ms, model_id, 
                        prompt_tokens, completion_tokens, http_status, error_text)
                       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)""",
                    self.run_id, result.started_at, result.finished_at,
                    result.latency_ms, self.model_id, result.tokens_in,
                    result.tokens_out, result.http_status, result.error_text
                )
        except Exception as e:
            # Don't let DB errors break the main flow
            print(f"DB error recording job: {e}")
            
    async def record_sample(self, stats: WindowStats, concurrency: int, queue_depth: int):
        """Record tuner sample"""
        if not self.pool or not self.run_id:
            return
            
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """INSERT INTO perf_samples 
                       (run_id, ts, window_sec, concurrency, queue_depth, 
                        throughput_rps, p50_ms, p95_ms, error_rate, tokens_in, tokens_out)
                       VALUES ($1, NOW(), $2, $3, $4, $5, $6, $7, $8, $9, $10)""",
                    self.run_id, 30, concurrency, queue_depth,
                    stats.throughput_rps, stats.p50_ms, stats.p95_ms,
                    stats.error_rate, stats.tokens_in, stats.tokens_out
                )
        except Exception as e:
            print(f"DB error recording sample: {e}")
            
    async def get_run_summary(self) -> Optional[Dict[str, Any]]:
        """Get summary of current run"""
        if not self.pool or not self.run_id:
            return None
            
        try:
            async with self.pool.acquire() as conn:
                # Get run info
                run_info = await conn.fetchrow(
                    "SELECT * FROM perf_runs WHERE run_id = $1", self.run_id
                )
                
                # Get job stats
                job_stats = await conn.fetchrow(
                    """SELECT COUNT(*) as total_jobs,
                              AVG(latency_ms) as avg_latency,
                              MAX(latency_ms) as max_latency,
                              SUM(completion_tokens) as total_tokens
                       FROM perf_jobs WHERE run_id = $1""",
                    self.run_id
                )
                
                # Get best throughput window
                best_window = await conn.fetchrow(
                    """SELECT concurrency, throughput_rps, p95_ms 
                       FROM perf_samples WHERE run_id = $1 
                       ORDER BY throughput_rps DESC LIMIT 1""",
                    self.run_id
                )
                
                return {
                    "run_id": str(self.run_id),
                    "model_id": run_info["model_id"],
                    "host": run_info["host"],
                    "started_at": run_info["started_at"],
                    "total_jobs": job_stats["total_jobs"] or 0,
                    "avg_latency_ms": float(job_stats["avg_latency"] or 0),
                    "max_latency_ms": job_stats["max_latency"] or 0,
                    "total_tokens": job_stats["total_tokens"] or 0,
                    "best_throughput_rps": float(best_window["throughput_rps"]) if best_window else 0,
                    "best_concurrency": best_window["concurrency"] if best_window else 0,
                    "best_p95_ms": best_window["p95_ms"] if best_window else 0
                }
                
        except Exception as e:
            print(f"DB error getting summary: {e}")
            return None