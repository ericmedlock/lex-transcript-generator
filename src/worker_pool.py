"""Bounded worker pool with async queue for LLM requests"""

import asyncio
import aiohttp
import time
import uuid
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@dataclass
class JobResult:
    job_id: str
    success: bool
    latency_ms: int
    tokens_in: int
    tokens_out: int
    http_status: Optional[int] = None
    error_text: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

@dataclass
class Job:
    job_id: str
    prompt: str
    model_id: str
    max_tokens: int = 128
    temperature: float = 0.7
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()

class WorkerPool:
    def __init__(self, endpoint_url: str, initial_concurrency: int = 2, 
                 max_concurrency: int = 4, queue_maxsize: int = 8,
                 request_timeout: int = 60):
        self.endpoint_url = endpoint_url
        self.concurrency = initial_concurrency
        self.max_concurrency = max_concurrency
        self.request_timeout = request_timeout
        
        self.job_queue = asyncio.Queue(maxsize=queue_maxsize)
        self.result_queue = asyncio.Queue()
        self.workers = []
        self.running = False
        
        # Metrics ring buffer for tuner
        self.metrics_buffer = []
        self.buffer_size = 1000
        
    async def start(self):
        """Start worker pool"""
        self.running = True
        await self._scale_workers(self.concurrency)
        logger.info(f"Worker pool started with {self.concurrency} workers")
        
    async def stop(self):
        """Stop worker pool gracefully"""
        self.running = False
        
        # Cancel all workers
        for worker in self.workers:
            worker.cancel()
        
        # Wait for workers to finish
        if self.workers:
            await asyncio.gather(*self.workers, return_exceptions=True)
        
        self.workers.clear()
        logger.info("Worker pool stopped")
        
    async def submit_job(self, job: Job) -> bool:
        """Submit job to queue, returns False if queue full"""
        try:
            self.job_queue.put_nowait(job)
            return True
        except asyncio.QueueFull:
            return False
            
    async def get_result(self) -> Optional[JobResult]:
        """Get completed job result"""
        try:
            return await asyncio.wait_for(self.result_queue.get(), timeout=0.1)
        except asyncio.TimeoutError:
            return None
            
    def get_queue_depth(self) -> int:
        """Get current queue depth"""
        return self.job_queue.qsize()
        
    async def scale_concurrency(self, new_concurrency: int):
        """Scale worker pool to new concurrency level"""
        new_concurrency = max(1, min(new_concurrency, self.max_concurrency))
        
        if new_concurrency == self.concurrency:
            return
            
        logger.info(f"Scaling workers: {self.concurrency} -> {new_concurrency}")
        await self._scale_workers(new_concurrency)
        self.concurrency = new_concurrency
        
    async def _scale_workers(self, target_count: int):
        """Internal method to scale workers"""
        current_count = len(self.workers)
        
        if target_count > current_count:
            # Add workers
            for _ in range(target_count - current_count):
                worker = asyncio.create_task(self._worker())
                self.workers.append(worker)
        elif target_count < current_count:
            # Remove workers
            workers_to_remove = self.workers[target_count:]
            self.workers = self.workers[:target_count]
            
            for worker in workers_to_remove:
                worker.cancel()
                
    async def _worker(self):
        """Worker coroutine that processes jobs"""
        session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.request_timeout))
        
        try:
            while self.running:
                try:
                    # Get job from queue
                    job = await asyncio.wait_for(self.job_queue.get(), timeout=1.0)
                    
                    # Process job with retry logic
                    result = await self._process_job(session, job)
                    
                    # Store result and metrics
                    await self.result_queue.put(result)
                    self._record_metrics(result)
                    
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.error(f"Worker error: {e}")
                    
        finally:
            await session.close()
            
    async def _process_job(self, session: aiohttp.ClientSession, job: Job) -> JobResult:
        """Process single job with retry logic"""
        max_retries = 3
        
        for attempt in range(max_retries):
            started_at = datetime.utcnow()
            
            try:
                payload = {
                    "model": job.model_id,
                    "messages": [{"role": "user", "content": job.prompt}],
                    "max_tokens": job.max_tokens,
                    "temperature": job.temperature
                }
                
                async with session.post(self.endpoint_url, json=payload) as resp:
                    finished_at = datetime.utcnow()
                    latency_ms = int((finished_at - started_at).total_seconds() * 1000)
                    
                    if resp.status == 200:
                        data = await resp.json()
                        
                        # Extract token counts
                        usage = data.get("usage", {})
                        tokens_in = usage.get("prompt_tokens", len(job.prompt.split()))
                        tokens_out = usage.get("completion_tokens", 0)
                        
                        return JobResult(
                            job_id=job.job_id,
                            success=True,
                            latency_ms=latency_ms,
                            tokens_in=tokens_in,
                            tokens_out=tokens_out,
                            http_status=resp.status,
                            started_at=started_at,
                            finished_at=finished_at
                        )
                    elif resp.status == 429:
                        # Rate limited - wait with jitter
                        wait_time = (2 ** attempt) + (time.time() % 1)
                        await asyncio.sleep(wait_time)
                        continue
                    elif resp.status >= 500:
                        # Server error - retry
                        if attempt < max_retries - 1:
                            wait_time = (2 ** attempt) + (time.time() % 1)
                            await asyncio.sleep(wait_time)
                            continue
                    
                    # Client error or final retry
                    error_text = await resp.text()
                    return JobResult(
                        job_id=job.job_id,
                        success=False,
                        latency_ms=latency_ms,
                        tokens_in=len(job.prompt.split()),
                        tokens_out=0,
                        http_status=resp.status,
                        error_text=error_text[:500],
                        started_at=started_at,
                        finished_at=finished_at
                    )
                    
            except Exception as e:
                if attempt == max_retries - 1:
                    finished_at = datetime.utcnow()
                    latency_ms = int((finished_at - started_at).total_seconds() * 1000)
                    
                    return JobResult(
                        job_id=job.job_id,
                        success=False,
                        latency_ms=latency_ms,
                        tokens_in=len(job.prompt.split()),
                        tokens_out=0,
                        error_text=str(e)[:500],
                        started_at=started_at,
                        finished_at=finished_at
                    )
                else:
                    # Wait before retry
                    wait_time = (2 ** attempt) + (time.time() % 1)
                    await asyncio.sleep(wait_time)
                    
    def _record_metrics(self, result: JobResult):
        """Record job metrics in ring buffer"""
        self.metrics_buffer.append(result)
        
        # Keep buffer size limited
        if len(self.metrics_buffer) > self.buffer_size:
            self.metrics_buffer.pop(0)
            
    def get_recent_metrics(self, window_seconds: int = 30) -> List[JobResult]:
        """Get metrics from recent time window"""
        cutoff_time = datetime.utcnow().timestamp() - window_seconds
        
        return [
            result for result in self.metrics_buffer
            if result.finished_at and result.finished_at.timestamp() > cutoff_time
        ]