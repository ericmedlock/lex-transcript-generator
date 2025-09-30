"""Main performance-enhanced LLM generator"""

import asyncio
import os
import signal
import sys
import time
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
import logging

from .worker_pool import WorkerPool, Job
from .tuner import ConcurrencyTuner
from .metrics_db import MetricsDB
from .server import MetricsServer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PerformanceGenerator:
    def __init__(self):
        # Load configuration from environment
        self.endpoint_url = os.getenv('LLM_ENDPOINT', 'http://127.0.0.1:1234/v1/chat/completions')
        self.model_id = os.getenv('MODEL_ID', 'meta-llama-3-8b-instruct')
        self.max_tokens = int(os.getenv('MAX_TOKENS', '128'))
        self.temperature = float(os.getenv('TEMPERATURE', '0.7'))
        
        # Concurrency settings
        self.concurrency_min = int(os.getenv('CONCURRENCY_MIN', '2'))
        self.concurrency_max = int(os.getenv('CONCURRENCY_MAX', '4'))
        self.concurrency_start = int(os.getenv('CONCURRENCY_START', '2'))
        
        # Performance targets
        self.target_p95_ms = int(os.getenv('TARGET_P95_MS', '2500'))
        self.target_error_rate = float(os.getenv('TARGET_ERROR_RATE', '0.03'))
        
        # Tuning parameters
        self.sample_window_sec = int(os.getenv('SAMPLE_WINDOW_SEC', '30'))
        self.tune_interval_sec = int(os.getenv('TUNE_INTERVAL_SEC', '15'))
        self.increase_step = int(os.getenv('INCREASE_STEP', '1'))
        self.decrease_step = int(os.getenv('DECREASE_STEP', '1'))
        
        # Queue and timeout settings
        self.backpressure_queue_max = int(os.getenv('BACKPRESSURE_QUEUE_MAX', '8'))
        self.request_timeout_sec = int(os.getenv('REQUEST_TIMEOUT_SEC', '60'))
        
        # Metrics server
        self.metrics_port = int(os.getenv('METRICS_PORT', '8088'))
        
        # Database
        self.perf_db_url = os.getenv('PERF_DB_URL')
        
        # Components
        self.worker_pool = None
        self.tuner = None
        self.metrics_db = None
        self.metrics_server = None
        
        # State
        self.running = False
        self.shutdown_event = asyncio.Event()
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.shutdown_event.set()
        
    async def initialize(self):
        """Initialize all components"""
        logger.info("Initializing performance generator...")
        
        # Initialize worker pool
        self.worker_pool = WorkerPool(
            endpoint_url=self.endpoint_url,
            initial_concurrency=self.concurrency_start,
            max_concurrency=self.concurrency_max,
            queue_maxsize=self.backpressure_queue_max,
            request_timeout=self.request_timeout_sec
        )
        
        # Initialize tuner
        self.tuner = ConcurrencyTuner(
            worker_pool=self.worker_pool,
            target_p95_ms=self.target_p95_ms,
            target_error_rate=self.target_error_rate,
            sample_window_sec=self.sample_window_sec,
            tune_interval_sec=self.tune_interval_sec,
            increase_step=self.increase_step,
            decrease_step=self.decrease_step,
            min_concurrency=self.concurrency_min,
            max_concurrency=self.concurrency_max
        )
        
        # Initialize metrics database
        if self.perf_db_url:
            self.metrics_db = MetricsDB(self.perf_db_url, self.model_id)
            await self.metrics_db.initialize()
            logger.info(f"Connected to metrics database: {self.metrics_db.run_id}")
        
        # Initialize metrics server
        self.metrics_server = MetricsServer(self.metrics_port)
        await self.metrics_server.start()
        
        logger.info("Initialization complete")
        
    async def start(self):
        """Start the performance generator"""
        await self.initialize()
        
        # Start components
        await self.worker_pool.start()
        await self.tuner.start()
        
        self.running = True
        logger.info("Performance generator started")
        
        # Start background tasks
        tasks = [
            asyncio.create_task(self._metrics_loop()),
            asyncio.create_task(self._job_processor_loop())
        ]
        
        try:
            # Wait for shutdown signal
            await self.shutdown_event.wait()
        finally:
            # Cancel background tasks
            for task in tasks:
                task.cancel()
            
            await self.shutdown()
            
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down performance generator...")
        
        self.running = False
        
        # Stop components in reverse order
        if self.tuner:
            await self.tuner.stop()
            
        if self.worker_pool:
            await self.worker_pool.stop()
            
        if self.metrics_server:
            await self.metrics_server.stop()
            
        if self.metrics_db:
            await self.metrics_db.close()
            
        logger.info("Shutdown complete")
        
    async def _metrics_loop(self):
        """Background loop to update metrics"""
        while self.running:
            try:
                # Get current stats
                stats = self.tuner.get_current_stats()
                
                if stats:
                    # Update metrics server
                    metrics_data = {
                        "concurrency": self.worker_pool.concurrency,
                        "queue_depth": self.worker_pool.get_queue_depth(),
                        "throughput_rps": stats.throughput_rps,
                        "p50_ms": stats.p50_ms,
                        "p95_ms": stats.p95_ms,
                        "error_rate": stats.error_rate,
                        "tokens_per_sec_in": stats.tokens_in / self.sample_window_sec,
                        "tokens_per_sec_out": stats.tokens_out / self.sample_window_sec
                    }
                    
                    await self.metrics_server.update_metrics(metrics_data)
                    
                    # Record to database
                    if self.metrics_db:
                        await self.metrics_db.record_sample(
                            stats, self.worker_pool.concurrency, 
                            self.worker_pool.get_queue_depth()
                        )
                
                await asyncio.sleep(5)  # Update every 5 seconds
                
            except Exception as e:
                logger.error(f"Metrics loop error: {e}")
                await asyncio.sleep(5)
                
    async def _job_processor_loop(self):
        """Background loop to process completed jobs"""
        while self.running:
            try:
                # Get completed job results
                result = await self.worker_pool.get_result()
                
                if result:
                    # Log job completion
                    status = "OK" if result.success else "FAIL"
                    logger.info(f"Job {result.job_id[:8]} {status} "
                               f"{result.latency_ms}ms "
                               f"{result.tokens_in}→{result.tokens_out} tokens "
                               f"HTTP:{result.http_status}")
                    
                    # Record to database
                    if self.metrics_db:
                        await self.metrics_db.record_job(result)
                        
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Job processor error: {e}")
                await asyncio.sleep(1)
                
    async def submit_job(self, prompt: str) -> bool:
        """Submit a job to the worker pool"""
        if not self.running:
            return False
            
        job = Job(
            job_id=str(uuid.uuid4()),
            prompt=prompt,
            model_id=self.model_id,
            max_tokens=self.max_tokens,
            temperature=self.temperature
        )
        
        success = await self.worker_pool.submit_job(job)
        
        if not success:
            logger.warning("Job queue full - backpressure activated")
            
        return success
        
    def get_status(self) -> Dict[str, Any]:
        """Get current system status"""
        stats = self.tuner.get_current_stats()
        
        return {
            "running": self.running,
            "concurrency": self.worker_pool.concurrency if self.worker_pool else 0,
            "queue_depth": self.worker_pool.get_queue_depth() if self.worker_pool else 0,
            "throughput_rps": stats.throughput_rps if stats else 0,
            "p95_ms": stats.p95_ms if stats else 0,
            "error_rate": stats.error_rate if stats else 0,
            "metrics_port": self.metrics_port,
            "run_id": str(self.metrics_db.run_id) if self.metrics_db else None
        }

# CLI interface
async def main():
    """Main entry point"""
    generator = PerformanceGenerator()
    
    try:
        await generator.start()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())