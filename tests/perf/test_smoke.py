"""Smoke tests for performance system"""

import pytest
import asyncio
import os
from unittest.mock import patch, AsyncMock
from aiohttp import web
from src.perf_generator import PerformanceGenerator

@pytest.fixture
async def mock_llm_server():
    """Mock LLM server for testing"""
    request_count = 0
    
    async def handler(request):
        nonlocal request_count
        request_count += 1
        
        # Simulate some latency
        await asyncio.sleep(0.1)
        
        response = {
            "choices": [{"message": {"content": f"Response {request_count}"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 15}
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
    
    yield url, lambda: request_count
    
    await site.stop()
    await runner.cleanup()

@pytest.mark.asyncio
async def test_smoke_basic_generation(mock_llm_server):
    """Smoke test: basic generation without database"""
    url, get_count = mock_llm_server
    
    # Set environment for test
    with patch.dict(os.environ, {
        'LLM_ENDPOINT': url,
        'CONCURRENCY_MIN': '1',
        'CONCURRENCY_MAX': '2',
        'CONCURRENCY_START': '1',
        'METRICS_PORT': '8089',  # Different port to avoid conflicts
        'TARGET_P95_MS': '5000',  # High threshold for test
        'SAMPLE_WINDOW_SEC': '5',
        'TUNE_INTERVAL_SEC': '3'
    }):
        generator = PerformanceGenerator()
        
        # Start generator
        start_task = asyncio.create_task(generator.start())
        
        # Wait for initialization
        await asyncio.sleep(1)
        
        # Submit some jobs
        prompts = [
            "Generate a short conversation",
            "Create a brief dialogue",
            "Write a simple exchange"
        ]
        
        submitted = 0
        for prompt in prompts:
            if await generator.submit_job(prompt):
                submitted += 1
                
        assert submitted == len(prompts)
        
        # Wait for processing
        await asyncio.sleep(2)
        
        # Check that requests were made
        assert get_count() >= submitted
        
        # Check status
        status = generator.get_status()
        assert status['running']
        assert status['concurrency'] >= 1
        
        # Shutdown
        generator.shutdown_event.set()
        
        try:
            await asyncio.wait_for(start_task, timeout=5)
        except asyncio.TimeoutError:
            start_task.cancel()

@pytest.mark.asyncio
async def test_smoke_concurrency_scaling(mock_llm_server):
    """Smoke test: concurrency scaling under load"""
    url, get_count = mock_llm_server
    
    with patch.dict(os.environ, {
        'LLM_ENDPOINT': url,
        'CONCURRENCY_MIN': '1',
        'CONCURRENCY_MAX': '3',
        'CONCURRENCY_START': '1',
        'METRICS_PORT': '8090',
        'TARGET_P95_MS': '1000',  # Low threshold to trigger scaling
        'SAMPLE_WINDOW_SEC': '3',
        'TUNE_INTERVAL_SEC': '2'
    }):
        generator = PerformanceGenerator()
        
        start_task = asyncio.create_task(generator.start())
        await asyncio.sleep(1)
        
        # Submit many jobs to trigger scaling
        for i in range(10):
            await generator.submit_job(f"Test prompt {i}")
            await asyncio.sleep(0.1)
            
        # Wait for tuner to potentially scale up
        await asyncio.sleep(5)
        
        status = generator.get_status()
        
        # Should have processed some jobs
        assert get_count() > 0
        
        # May have scaled up due to load
        assert status['concurrency'] >= 1
        assert status['concurrency'] <= 3
        
        generator.shutdown_event.set()
        
        try:
            await asyncio.wait_for(start_task, timeout=5)
        except asyncio.TimeoutError:
            start_task.cancel()

@pytest.mark.asyncio
async def test_smoke_metrics_server(mock_llm_server):
    """Smoke test: metrics server functionality"""
    url, get_count = mock_llm_server
    
    with patch.dict(os.environ, {
        'LLM_ENDPOINT': url,
        'CONCURRENCY_START': '1',
        'METRICS_PORT': '8091'
    }):
        generator = PerformanceGenerator()
        
        start_task = asyncio.create_task(generator.start())
        await asyncio.sleep(1)
        
        # Test metrics endpoint
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get('http://localhost:8091/metrics') as resp:
                assert resp.status == 200
                data = await resp.json()
                
                # Check expected fields
                assert 'concurrency' in data
                assert 'queue_depth' in data
                assert 'throughput_rps' in data
                assert 'last_updated' in data
                
            # Test health endpoint
            async with session.get('http://localhost:8091/health') as resp:
                assert resp.status == 200
                data = await resp.json()
                assert data['status'] == 'ok'
        
        generator.shutdown_event.set()
        
        try:
            await asyncio.wait_for(start_task, timeout=5)
        except asyncio.TimeoutError:
            start_task.cancel()

def test_configuration_loading():
    """Test configuration loading from environment"""
    with patch.dict(os.environ, {
        'CONCURRENCY_MIN': '3',
        'CONCURRENCY_MAX': '8',
        'TARGET_P95_MS': '1500',
        'MODEL_ID': 'custom-model'
    }):
        generator = PerformanceGenerator()
        
        assert generator.concurrency_min == 3
        assert generator.concurrency_max == 8
        assert generator.target_p95_ms == 1500
        assert generator.model_id == 'custom-model'

def test_configuration_defaults():
    """Test default configuration values"""
    # Clear relevant env vars
    env_vars = [
        'CONCURRENCY_MIN', 'CONCURRENCY_MAX', 'TARGET_P95_MS', 
        'MODEL_ID', 'TEMPERATURE', 'MAX_TOKENS'
    ]
    
    with patch.dict(os.environ, {var: '' for var in env_vars}, clear=True):
        generator = PerformanceGenerator()
        
        # Check defaults
        assert generator.concurrency_min == 2
        assert generator.concurrency_max == 4
        assert generator.target_p95_ms == 2500
        assert generator.model_id == 'meta-llama-3-8b-instruct'
        assert generator.temperature == 0.7
        assert generator.max_tokens == 128