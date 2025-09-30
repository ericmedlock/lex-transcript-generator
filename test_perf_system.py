#!/usr/bin/env python3
"""
Quick test script to verify the performance system works
Run this to test the basic functionality without full setup
"""

import asyncio
import os
import sys
from unittest.mock import patch
from aiohttp import web

async def mock_llm_server():
    """Simple mock LLM server for testing"""
    async def handler(request):
        await asyncio.sleep(0.1)  # Simulate processing time
        return web.json_response({
            "choices": [{"message": {"content": "Test response"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 15}
        })
    
    app = web.Application()
    app.router.add_post('/v1/chat/completions', handler)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 0)
    await site.start()
    
    port = site._server.sockets[0].getsockname()[1]
    url = f"http://localhost:{port}/v1/chat/completions"
    
    print(f"Mock LLM server started on {url}")
    return url, site, runner

async def test_basic_functionality():
    """Test basic performance system functionality"""
    print("Starting basic functionality test...")
    
    # Start mock server
    url, site, runner = await mock_llm_server()
    
    try:
        # Import and configure
        from src.perf_generator import PerformanceGenerator
        
        with patch.dict(os.environ, {
            'LLM_ENDPOINT': url,
            'CONCURRENCY_MIN': '1',
            'CONCURRENCY_MAX': '2',
            'CONCURRENCY_START': '1',
            'METRICS_PORT': '8099',  # Unique port
            'TARGET_P95_MS': '5000',  # High threshold
            'SAMPLE_WINDOW_SEC': '5',
            'TUNE_INTERVAL_SEC': '3'
        }):
            generator = PerformanceGenerator()
            
            # Start generator
            print("Starting performance generator...")
            start_task = asyncio.create_task(generator.start())
            
            # Wait for initialization
            await asyncio.sleep(2)
            
            # Submit test jobs
            print("Submitting test jobs...")
            test_prompts = [
                "Generate a short conversation",
                "Create a brief dialogue",
                "Write a simple exchange"
            ]
            
            for i, prompt in enumerate(test_prompts):
                success = await generator.submit_job(prompt)
                print(f"Job {i+1}: {'✓' if success else '✗'}")
                
            # Wait for processing
            print("Waiting for job processing...")
            await asyncio.sleep(3)
            
            # Check status
            status = generator.get_status()
            print(f"Status: {status}")
            
            # Test metrics endpoint
            print("Testing metrics endpoint...")
            import aiohttp
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get('http://localhost:8099/metrics') as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            print(f"Metrics: concurrency={data.get('concurrency')}, "
                                  f"throughput={data.get('throughput_rps'):.2f}")
                        else:
                            print(f"Metrics endpoint error: {resp.status}")
            except Exception as e:
                print(f"Metrics test failed: {e}")
            
            print("✓ Basic functionality test completed successfully!")
            
            # Shutdown
            generator.shutdown_event.set()
            await asyncio.wait_for(start_task, timeout=5)
            
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup mock server
        await site.stop()
        await runner.cleanup()

async def test_imports():
    """Test that all modules can be imported"""
    print("Testing imports...")
    
    try:
        from src.worker_pool import WorkerPool, Job, JobResult
        from src.tuner import ConcurrencyTuner, WindowStats
        from src.metrics_db import MetricsDB
        from src.server import MetricsServer
        from src.perf_generator import PerformanceGenerator
        from src.bench import BenchmarkRunner
        print("✓ All imports successful!")
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function"""
    print("=" * 50)
    print("Performance System Test")
    print("=" * 50)
    
    # Test imports first
    if not await test_imports():
        print("Import test failed - cannot continue")
        sys.exit(1)
    
    # Test basic functionality
    await test_basic_functionality()
    
    print("\n" + "=" * 50)
    print("Test completed!")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())