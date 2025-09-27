#!/usr/bin/env python3
"""
Check job queue status
"""

import sqlite3
from pathlib import Path

DB_PATH = "data/transcript_platform.db"

def check_jobs():
    if not Path(DB_PATH).exists():
        print("❌ Database not found")
        return
    
    conn = sqlite3.connect(DB_PATH)
    
    # Job status breakdown
    statuses = conn.execute(
        "SELECT status, COUNT(*) FROM jobs GROUP BY status"
    ).fetchall()
    
    print("📋 Job Queue Status:")
    for status, count in statuses:
        print(f"  {status}: {count}")
    
    # Recent jobs
    recent = conn.execute(
        "SELECT id, job_type, status, created_at FROM jobs ORDER BY created_at DESC LIMIT 5"
    ).fetchall()
    
    print("\n🕒 Recent Jobs:")
    for job_id, job_type, status, created_at in recent:
        print(f"  {job_id[:8]} | {job_type} | {status} | {created_at}")
    
    conn.close()

if __name__ == "__main__":
    check_jobs()