#!/usr/bin/env python3
"""
Simple CLI wrapper for the performance-enhanced LLM generator
Windows-compatible alternative to Makefile
"""

import sys
import os
import subprocess
import asyncio
import asyncpg

def install():
    """Install dependencies"""
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

async def migrate():
    """Apply database migrations"""
    db_url = os.getenv('PERF_DB_URL')
    if not db_url:
        print("Error: PERF_DB_URL environment variable not set")
        sys.exit(1)
    
    try:
        with open('db/migrations/001_perf.sql', 'r') as f:
            sql = f.read()
        
        conn = await asyncpg.connect(db_url)
        await conn.execute(sql)
        await conn.close()
        print("Database migration completed successfully")
    except Exception as e:
        print(f"Migration failed: {e}")
        sys.exit(1)

def run_generator():
    """Start performance generator"""
    subprocess.run([sys.executable, "-m", "src.perf_generator"])

def run_bench():
    """Run benchmark"""
    args = sys.argv[2:] if len(sys.argv) > 2 else []
    subprocess.run([sys.executable, "-m", "src.bench"] + args)

def run_tests():
    """Run tests"""
    subprocess.run([sys.executable, "-m", "pytest", "tests/perf/", "-v"])

def main():
    if len(sys.argv) < 2:
        print("Usage: python run_perf.py <command>")
        print("Commands: install, migrate, run, bench, test")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "install":
        install()
    elif command == "migrate":
        asyncio.run(migrate())
    elif command == "run":
        run_generator()
    elif command == "bench":
        run_bench()
    elif command == "test":
        run_tests()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()