"""Tests for concurrency tuner"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from datetime import datetime
from src.tuner import ConcurrencyTuner, WindowStats
from src.worker_pool import WorkerPool, JobResult

class MockWorkerPool:
    def __init__(self, initial_concurrency=2):
        self.concurrency = initial_concurrency
        self.max_concurrency = 4
        self.queue_depth = 0
        self.metrics_buffer = []
        
    async def scale_concurrency(self, new_concurrency):
        self.concurrency = new_concurrency
        
    def get_queue_depth(self):
        return self.queue_depth
        
    def get_recent_metrics(self, window_seconds):
        return self.metrics_buffer

@pytest.fixture
def mock_worker_pool():
    return MockWorkerPool()

@pytest.fixture
def tuner(mock_worker_pool):
    return ConcurrencyTuner(
        worker_pool=mock_worker_pool,
        target_p95_ms=2500,
        target_error_rate=0.03,
        sample_window_sec=30,
        tune_interval_sec=15,
        min_concurrency=2,
        max_concurrency=4
    )

def create_job_result(latency_ms=1000, success=True, tokens_in=10, tokens_out=20):
    """Helper to create JobResult"""
    return JobResult(
        job_id="test-job",
        success=success,
        latency_ms=latency_ms,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        started_at=datetime.utcnow(),
        finished_at=datetime.utcnow()
    )

def test_tuner_decrease_on_high_latency(tuner, mock_worker_pool):
    """Test tuner decreases concurrency on high latency"""
    # Setup high latency metrics
    mock_worker_pool.metrics_buffer = [
        create_job_result(latency_ms=3000) for _ in range(10)
    ]
    
    stats = tuner._calculate_window_stats()
    assert stats is not None
    assert stats.p95_ms > tuner.target_p95_ms
    
    decision = tuner._make_tuning_decision(stats)
    assert decision < 0  # Should decrease

def test_tuner_decrease_on_high_error_rate(tuner, mock_worker_pool):
    """Test tuner decreases concurrency on high error rate"""
    # Setup high error rate metrics
    mock_worker_pool.metrics_buffer = [
        create_job_result(success=False) for _ in range(5)
    ] + [
        create_job_result(success=True) for _ in range(5)
    ]
    
    stats = tuner._calculate_window_stats()
    assert stats is not None
    assert stats.error_rate > tuner.target_error_rate
    
    decision = tuner._make_tuning_decision(stats)
    assert decision < 0  # Should decrease

def test_tuner_increase_on_queue_backlog(tuner, mock_worker_pool):
    """Test tuner increases concurrency on sustained queue backlog"""
    # Setup good metrics but high queue depth
    mock_worker_pool.metrics_buffer = [
        create_job_result(latency_ms=1000) for _ in range(10)
    ]
    mock_worker_pool.queue_depth = 5  # Higher than concurrency
    
    stats = tuner._calculate_window_stats()
    assert stats is not None
    
    decision = tuner._make_tuning_decision(stats)
    assert decision > 0  # Should increase

def test_tuner_revert_on_performance_degradation(tuner, mock_worker_pool):
    """Test tuner reverts changes that worsen performance"""
    # Setup initial good stats
    initial_stats = WindowStats(
        throughput_rps=10.0,
        p50_ms=1000,
        p95_ms=1500,
        error_rate=0.01,
        total_jobs=10,
        tokens_in=100,
        tokens_out=200,
        window_start=datetime.utcnow(),
        window_end=datetime.utcnow()
    )
    
    tuner.previous_stats = initial_stats
    tuner.last_change_time = asyncio.get_event_loop().time()
    tuner.last_change_direction = 1  # Previous increase
    
    # Setup worse current stats
    mock_worker_pool.metrics_buffer = [
        create_job_result(latency_ms=1000) for _ in range(5)  # Lower throughput
    ]
    
    current_stats = tuner._calculate_window_stats()
    assert current_stats.throughput_rps < initial_stats.throughput_rps
    
    # Should revert (decrease to undo previous increase)
    assert tuner._should_revert_change(current_stats)

def test_window_stats_calculation(tuner, mock_worker_pool):
    """Test window statistics calculation"""
    # Setup mixed metrics
    mock_worker_pool.metrics_buffer = [
        create_job_result(latency_ms=1000, tokens_in=10, tokens_out=20),
        create_job_result(latency_ms=1500, tokens_in=15, tokens_out=25),
        create_job_result(latency_ms=2000, tokens_in=20, tokens_out=30),
        create_job_result(success=False, latency_ms=500, tokens_in=5, tokens_out=0)
    ]
    
    stats = tuner._calculate_window_stats()
    
    assert stats is not None
    assert stats.total_jobs == 4
    assert stats.error_rate == 0.25  # 1 failed out of 4
    assert stats.p50_ms == 1500  # Median of successful jobs
    assert stats.tokens_in == 50  # Sum of all input tokens
    assert stats.tokens_out == 75  # Sum of all output tokens

@pytest.mark.asyncio
async def test_tuner_lifecycle(tuner):
    """Test tuner start/stop lifecycle"""
    assert not tuner.running
    
    await tuner.start()
    assert tuner.running
    assert tuner.tuner_task is not None
    
    await tuner.stop()
    assert not tuner.running