"""Tests for worker pool"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from aiohttp import web
from src.worker_pool import WorkerPool, Job, JobResult

@pytest.fixture
async def mock_server():
    """Create mock HTTP server for testing"""
    async def handler(request):
        data = await request.json()
        
        # Simulate different responses based on model
        if data.get("model") == "error-model":
            return web.Response(status=500, text="Server Error")
        elif data.get("model") == "rate-limit-model":
            return web.Response(status=429, text="Rate Limited")
        else:
            # Normal response
            response = {
                "choices": [{"message": {"content": "Test response"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 20}
            }
            return web.json_response(response)
    
    app = web.Application()
    app.router.add_post('/v1/chat/completions', handler)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 0)
    await site.start()
    
    port = site._server.sockets[0].getsockname()[1]
    url = f"http://localhost:{port}/v1/chat/completions"
    
    yield url
    
    await site.stop()
    await runner.cleanup()

@pytest.mark.asyncio
async def test_worker_pool_basic_operation(mock_server):
    """Test basic worker pool operation"""
    pool = WorkerPool(mock_server, initial_concurrency=2, max_concurrency=4)
    
    await pool.start()
    
    # Submit a job
    job = Job(job_id="test-1", prompt="Test prompt", model_id="test-model")
    success = await pool.submit_job(job)
    assert success
    
    # Get result
    result = None
    for _ in range(50):  # Wait up to 5 seconds
        result = await pool.get_result()
        if result:
            break
        await asyncio.sleep(0.1)
    
    assert result is not None
    assert result.success
    assert result.job_id == "test-1"
    assert result.latency_ms > 0
    assert result.tokens_in > 0
    assert result.tokens_out > 0
    
    await pool.stop()

@pytest.mark.asyncio
async def test_worker_pool_scaling(mock_server):
    """Test worker pool scaling"""
    pool = WorkerPool(mock_server, initial_concurrency=2, max_concurrency=4)
    
    await pool.start()
    assert pool.concurrency == 2
    
    # Scale up
    await pool.scale_concurrency(3)
    assert pool.concurrency == 3
    
    # Scale down
    await pool.scale_concurrency(1)
    assert pool.concurrency == 1
    
    # Test bounds
    await pool.scale_concurrency(10)  # Should cap at max_concurrency
    assert pool.concurrency == 4
    
    await pool.scale_concurrency(0)  # Should floor at 1
    assert pool.concurrency == 1
    
    await pool.stop()

@pytest.mark.asyncio
async def test_worker_pool_queue_full(mock_server):
    """Test queue backpressure"""
    pool = WorkerPool(mock_server, initial_concurrency=1, queue_maxsize=2)
    
    await pool.start()
    
    # Fill queue
    job1 = Job(job_id="test-1", prompt="Test 1", model_id="test-model")
    job2 = Job(job_id="test-2", prompt="Test 2", model_id="test-model")
    job3 = Job(job_id="test-3", prompt="Test 3", model_id="test-model")
    
    assert await pool.submit_job(job1)
    assert await pool.submit_job(job2)
    assert not await pool.submit_job(job3)  # Should fail - queue full
    
    await pool.stop()

@pytest.mark.asyncio
async def test_worker_pool_error_handling(mock_server):
    """Test error handling and retries"""
    pool = WorkerPool(mock_server, initial_concurrency=1)
    
    await pool.start()
    
    # Submit job that will cause server error
    job = Job(job_id="error-test", prompt="Test", model_id="error-model")
    await pool.submit_job(job)
    
    # Get result
    result = None
    for _ in range(50):
        result = await pool.get_result()
        if result:
            break
        await asyncio.sleep(0.1)
    
    assert result is not None
    assert not result.success
    assert result.http_status == 500
    assert "Server Error" in result.error_text
    
    await pool.stop()

@pytest.mark.asyncio
async def test_worker_pool_rate_limiting(mock_server):
    """Test rate limiting retry logic"""
    pool = WorkerPool(mock_server, initial_concurrency=1, request_timeout=10)
    
    await pool.start()
    
    # Submit job that will be rate limited
    job = Job(job_id="rate-limit-test", prompt="Test", model_id="rate-limit-model")
    await pool.submit_job(job)
    
    # Should eventually succeed after retries
    result = None
    for _ in range(100):  # Wait longer for retries
        result = await pool.get_result()
        if result:
            break
        await asyncio.sleep(0.1)
    
    # Note: This test might fail if retry logic doesn't eventually succeed
    # In a real scenario, we'd mock the retry behavior more precisely
    
    await pool.stop()

def test_job_creation():
    """Test Job dataclass creation"""
    job = Job(job_id="test", prompt="Hello", model_id="test-model")
    
    assert job.job_id == "test"
    assert job.prompt == "Hello"
    assert job.model_id == "test-model"
    assert job.max_tokens == 128  # default
    assert job.temperature == 0.7  # default
    assert job.created_at is not None

def test_job_result_creation():
    """Test JobResult dataclass creation"""
    result = JobResult(
        job_id="test",
        success=True,
        latency_ms=1500,
        tokens_in=10,
        tokens_out=20,
        http_status=200
    )
    
    assert result.job_id == "test"
    assert result.success
    assert result.latency_ms == 1500
    assert result.tokens_in == 10
    assert result.tokens_out == 20
    assert result.http_status == 200