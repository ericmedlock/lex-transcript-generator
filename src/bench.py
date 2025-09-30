"""Benchmark CLI for performance testing"""

import asyncio
import argparse
import time
import sys
from pathlib import Path
from .perf_generator import PerformanceGenerator

class BenchmarkRunner:
    def __init__(self, generator: PerformanceGenerator):
        self.generator = generator
        self.test_prompts = [
            "Generate a short conversation between a patient and receptionist scheduling an appointment.",
            "Create a brief dialogue about rescheduling a medical appointment.",
            "Write a conversation where a patient calls to cancel their appointment.",
            "Generate a short exchange about insurance verification for an appointment.",
            "Create a dialogue about scheduling an urgent same-day appointment."
        ]
        
    async def run_benchmark(self, jobs: int = None, duration_sec: int = None, 
                          prompt_file: str = None):
        """Run benchmark with specified parameters"""
        
        # Load custom prompts if provided
        prompts = self.test_prompts
        if prompt_file and Path(prompt_file).exists():
            with open(prompt_file, 'r') as f:
                prompts = [line.strip() for line in f if line.strip()]
                
        print(f"Starting benchmark with {len(prompts)} prompt variations")
        print(f"Target: {jobs or 'unlimited'} jobs, {duration_sec or 'unlimited'} seconds")
        print(f"Metrics: http://localhost:{self.generator.metrics_port}/metrics")
        print("-" * 60)
        
        start_time = time.time()
        jobs_submitted = 0
        prompt_index = 0
        
        # Submit jobs until limits reached
        while True:
            # Check time limit
            if duration_sec and (time.time() - start_time) >= duration_sec:
                break
                
            # Check job limit
            if jobs and jobs_submitted >= jobs:
                break
                
            # Submit job
            prompt = prompts[prompt_index % len(prompts)]
            success = await self.generator.submit_job(prompt)
            
            if success:
                jobs_submitted += 1
                prompt_index += 1
                
                # Progress update every 100 jobs
                if jobs_submitted % 100 == 0:
                    elapsed = time.time() - start_time
                    rate = jobs_submitted / elapsed
                    status = self.generator.get_status()
                    print(f"Submitted: {jobs_submitted} jobs, "
                          f"Rate: {rate:.1f} jobs/sec, "
                          f"Concurrency: {status['concurrency']}, "
                          f"Queue: {status['queue_depth']}")
            else:
                # Backpressure - wait briefly
                await asyncio.sleep(0.1)
                
            # Small delay to avoid overwhelming
            await asyncio.sleep(0.01)
            
        # Wait for completion
        print(f"\nSubmitted {jobs_submitted} jobs, waiting for completion...")
        
        # Monitor until queue is empty
        while True:
            status = self.generator.get_status()
            if status['queue_depth'] == 0:
                break
            print(f"Queue depth: {status['queue_depth']}, "
                  f"Throughput: {status['throughput_rps']:.2f} RPS")
            await asyncio.sleep(2)
            
        # Final summary
        total_time = time.time() - start_time
        await self.print_summary(total_time, jobs_submitted)
        
    async def print_summary(self, total_time: float, jobs_submitted: int):
        """Print benchmark summary"""
        print("\n" + "=" * 60)
        print("BENCHMARK SUMMARY")
        print("=" * 60)
        
        # Get final stats
        if self.generator.metrics_db:
            summary = await self.generator.metrics_db.get_run_summary()
            if summary:
                print(f"Run ID: {summary['run_id']}")
                print(f"Model: {summary['model_id']}")
                print(f"Host: {summary['host']}")
                print(f"Duration: {total_time:.1f} seconds")
                print(f"Jobs Submitted: {jobs_submitted}")
                print(f"Jobs Completed: {summary['total_jobs']}")
                print(f"Average Latency: {summary['avg_latency_ms']:.1f} ms")
                print(f"Max Latency: {summary['max_latency_ms']} ms")
                print(f"Total Tokens: {summary['total_tokens']}")
                print(f"Best Throughput: {summary['best_throughput_rps']:.2f} RPS")
                print(f"Best Concurrency: {summary['best_concurrency']}")
                print(f"Best P95 Latency: {summary['best_p95_ms']} ms")
            else:
                print("Could not retrieve run summary from database")
        else:
            print("No database configured - limited summary available")
            print(f"Duration: {total_time:.1f} seconds")
            print(f"Jobs Submitted: {jobs_submitted}")
            
        status = self.generator.get_status()
        print(f"Final Concurrency: {status['concurrency']}")
        print(f"Final Queue Depth: {status['queue_depth']}")

async def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(description='LLM Performance Benchmark')
    parser.add_argument('--jobs', type=int, help='Number of jobs to submit')
    parser.add_argument('--duration-sec', type=int, help='Duration in seconds')
    parser.add_argument('--prompt-file', help='File with custom prompts (one per line)')
    parser.add_argument('--model', help='Model ID override')
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.jobs and not args.duration_sec:
        print("Error: Must specify either --jobs or --duration-sec")
        sys.exit(1)
        
    # Override model if specified
    if args.model:
        import os
        os.environ['MODEL_ID'] = args.model
        
    # Create and start generator
    generator = PerformanceGenerator()
    
    try:
        # Start generator in background
        generator_task = asyncio.create_task(generator.start())
        
        # Wait for initialization
        await asyncio.sleep(2)
        
        # Run benchmark
        runner = BenchmarkRunner(generator)
        await runner.run_benchmark(
            jobs=args.jobs,
            duration_sec=args.duration_sec,
            prompt_file=args.prompt_file
        )
        
    except KeyboardInterrupt:
        print("\nBenchmark interrupted by user")
    except Exception as e:
        print(f"Benchmark error: {e}")
        sys.exit(1)
    finally:
        # Shutdown generator
        generator.shutdown_event.set()
        try:
            await asyncio.wait_for(generator_task, timeout=10)
        except asyncio.TimeoutError:
            print("Warning: Generator shutdown timed out")

if __name__ == "__main__":
    asyncio.run(main())