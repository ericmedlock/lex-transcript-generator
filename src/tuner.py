"""Dynamic concurrency tuner with hill-climbing algorithm"""

import asyncio
import time
import statistics
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from .worker_pool import JobResult

logger = logging.getLogger(__name__)

@dataclass
class WindowStats:
    throughput_rps: float
    p50_ms: int
    p95_ms: int
    error_rate: float
    total_jobs: int
    tokens_in: int
    tokens_out: int
    window_start: datetime
    window_end: datetime

class ConcurrencyTuner:
    def __init__(self, worker_pool, target_p95_ms: int = 2500, 
                 target_error_rate: float = 0.03, sample_window_sec: int = 30,
                 tune_interval_sec: int = 15, increase_step: int = 1, 
                 decrease_step: int = 1, min_concurrency: int = 2,
                 max_concurrency: int = 4):
        
        self.worker_pool = worker_pool
        self.target_p95_ms = target_p95_ms
        self.target_error_rate = target_error_rate
        self.sample_window_sec = sample_window_sec
        self.tune_interval_sec = tune_interval_sec
        self.increase_step = increase_step
        self.decrease_step = decrease_step
        self.min_concurrency = min_concurrency
        self.max_concurrency = max_concurrency
        
        self.running = False
        self.tuner_task = None
        
        # State tracking
        self.previous_stats = None
        self.previous_concurrency = None
        self.last_change_time = None
        self.last_change_direction = None
        
        # Performance history
        self.stats_history = []
        self.max_history = 100
        
    async def start(self):
        """Start the tuner"""
        self.running = True
        self.tuner_task = asyncio.create_task(self._tuner_loop())
        logger.info(f"Tuner started: target_p95={self.target_p95_ms}ms, target_error_rate={self.target_error_rate}")
        
    async def stop(self):
        """Stop the tuner"""
        self.running = False
        if self.tuner_task:
            self.tuner_task.cancel()
            try:
                await self.tuner_task
            except asyncio.CancelledError:
                pass
        logger.info("Tuner stopped")
        
    async def _tuner_loop(self):
        """Main tuner loop"""
        while self.running:
            try:
                await asyncio.sleep(self.tune_interval_sec)
                
                # Collect metrics from recent window
                stats = self._calculate_window_stats()
                
                if stats and stats.total_jobs > 0:
                    # Make tuning decision
                    decision = self._make_tuning_decision(stats)
                    
                    # Apply decision
                    if decision != 0:
                        new_concurrency = max(
                            self.min_concurrency,
                            min(self.max_concurrency, self.worker_pool.concurrency + decision)
                        )
                        
                        if new_concurrency != self.worker_pool.concurrency:
                            await self._apply_concurrency_change(new_concurrency, stats, decision)
                    
                    # Store stats for next iteration
                    self.previous_stats = stats
                    self.previous_concurrency = self.worker_pool.concurrency
                    
                    # Keep history
                    self.stats_history.append(stats)
                    if len(self.stats_history) > self.max_history:
                        self.stats_history.pop(0)
                        
            except Exception as e:
                logger.error(f"Tuner error: {e}")
                
    def _calculate_window_stats(self) -> Optional[WindowStats]:
        """Calculate performance stats for recent window"""
        metrics = self.worker_pool.get_recent_metrics(self.sample_window_sec)
        
        if not metrics:
            return None
            
        # Calculate latencies
        latencies = [m.latency_ms for m in metrics if m.success]
        if not latencies:
            return None
            
        # Calculate stats
        window_duration = self.sample_window_sec
        throughput_rps = len(metrics) / window_duration
        
        p50_ms = int(statistics.median(latencies))
        p95_ms = int(statistics.quantiles(latencies, n=20)[18]) if len(latencies) >= 20 else max(latencies)
        
        error_count = sum(1 for m in metrics if not m.success)
        error_rate = error_count / len(metrics) if metrics else 0.0
        
        tokens_in = sum(m.tokens_in for m in metrics)
        tokens_out = sum(m.tokens_out for m in metrics)
        
        return WindowStats(
            throughput_rps=throughput_rps,
            p50_ms=p50_ms,
            p95_ms=p95_ms,
            error_rate=error_rate,
            total_jobs=len(metrics),
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            window_start=datetime.utcnow(),
            window_end=datetime.utcnow()
        )
        
    def _make_tuning_decision(self, current_stats: WindowStats) -> int:
        """Make tuning decision based on current stats"""
        
        # Check if we're violating constraints
        if (current_stats.error_rate > self.target_error_rate or 
            current_stats.p95_ms > self.target_p95_ms):
            logger.info(f"Constraint violation: error_rate={current_stats.error_rate:.3f} "
                       f"p95={current_stats.p95_ms}ms - decreasing concurrency")
            return -self.decrease_step
            
        # Check if we should revert recent change
        if self._should_revert_change(current_stats):
            revert_direction = -self.last_change_direction if self.last_change_direction else 0
            logger.info(f"Reverting previous change: {revert_direction}")
            return revert_direction
            
        # Check if we should increase concurrency
        if self._should_increase_concurrency(current_stats):
            logger.info(f"Increasing concurrency: throughput={current_stats.throughput_rps:.2f} "
                       f"queue_depth={self.worker_pool.get_queue_depth()}")
            return self.increase_step
            
        # Hold steady
        return 0
        
    def _should_revert_change(self, current_stats: WindowStats) -> bool:
        """Check if we should revert the last change"""
        if not self.previous_stats or not self.last_change_time:
            return False
            
        # Only consider revert if change was recent
        if time.time() - self.last_change_time > self.tune_interval_sec * 2:
            return False
            
        # Check if throughput worsened significantly
        throughput_change = (current_stats.throughput_rps - self.previous_stats.throughput_rps) / self.previous_stats.throughput_rps
        if throughput_change < -0.05:  # 5% worse
            return True
            
        # Check if latency increased significantly
        latency_change = (current_stats.p95_ms - self.previous_stats.p95_ms) / self.previous_stats.p95_ms
        if latency_change > 0.10:  # 10% worse
            return True
            
        return False
        
    def _should_increase_concurrency(self, current_stats: WindowStats) -> bool:
        """Check if we should increase concurrency"""
        if self.worker_pool.concurrency >= self.max_concurrency:
            return False
            
        # Increase if throughput improved or queue has sustained backlog
        queue_depth = self.worker_pool.get_queue_depth()
        
        # Check for sustained queue backlog
        if queue_depth > self.worker_pool.concurrency:
            return True
            
        # Check for throughput improvement opportunity
        if self.previous_stats:
            throughput_change = (current_stats.throughput_rps - self.previous_stats.throughput_rps) / self.previous_stats.throughput_rps
            if throughput_change >= 0.03:  # 3% improvement
                return True
                
        return False
        
    async def _apply_concurrency_change(self, new_concurrency: int, stats: WindowStats, decision: int):
        """Apply concurrency change and log it"""
        old_concurrency = self.worker_pool.concurrency
        
        await self.worker_pool.scale_concurrency(new_concurrency)
        
        self.last_change_time = time.time()
        self.last_change_direction = decision
        
        decision_str = "UP" if decision > 0 else "DOWN" if decision < 0 else "HOLD"
        
        logger.info(f"Tuner decision: conc={old_concurrency}->{new_concurrency} "
                   f"q={self.worker_pool.get_queue_depth()} "
                   f"rps={stats.throughput_rps:.2f} "
                   f"p95={stats.p95_ms}ms "
                   f"err={stats.error_rate:.3f} "
                   f"decision={decision_str}")
                   
    def get_current_stats(self) -> Optional[WindowStats]:
        """Get current performance stats"""
        return self._calculate_window_stats()
        
    def get_stats_history(self) -> List[WindowStats]:
        """Get performance history"""
        return self.stats_history.copy()