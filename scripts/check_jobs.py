#!/usr/bin/env python3
"""
Check job queue status
"""

import psycopg2

DB_CONFIG = {
    'host': 'EPM_DELL',
    'port': 5432,
    'database': 'calllab',
    'user': 'postgres',
    'password': 'pass'
}

def check_jobs():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return
    
    cur = conn.cursor()
    
    # Job status breakdown
    cur.execute(
        "SELECT status, COUNT(*) FROM jobs GROUP BY status"
    )
    statuses = cur.fetchall()
    
    print("📋 Job Queue Status:")
    for status, count in statuses:
        print(f"  {status}: {count}")
    
    # Recent jobs
    cur.execute(
        "SELECT id, scenario_id, status, created_at FROM jobs ORDER BY created_at DESC LIMIT 5"
    )
    recent = cur.fetchall()
    
    cur.close()
    
    print("\n🕒 Recent Jobs:")
    for job_id, scenario_id, status, created_at in recent:
        print(f"  {job_id[:8]} | {scenario_id[:8]} | {status} | {created_at}")
    
    conn.close()

if __name__ == "__main__":
    check_jobs()