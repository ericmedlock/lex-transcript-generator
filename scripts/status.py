#!/usr/bin/env python3
"""Quick system status check"""

import json
import psycopg2
from datetime import datetime, timedelta

def check_status():
    """Quick status overview"""
    try:
        # Load config
        with open('config/orchestrator_config.json', 'r') as f:
            config = json.load(f)
        
        db_config = config.get("db_config", {})
        
        # Connect to database
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()
        
        # Get basic stats
        cur.execute("SELECT COUNT(*) FROM nodes WHERE status = 'online'")
        online_nodes = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM jobs WHERE status = 'pending'")
        pending_jobs = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM jobs WHERE status = 'running'")
        running_jobs = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM conversations")
        total_conversations = cur.fetchone()[0]
        
        # Recent activity
        cur.execute("SELECT COUNT(*) FROM conversations WHERE created_at > NOW() - INTERVAL '1 hour'")
        recent_conversations = cur.fetchone()[0]
        
        print(f"System Status:")
        print(f"  Online Nodes: {online_nodes}")
        print(f"  Pending Jobs: {pending_jobs}")
        print(f"  Running Jobs: {running_jobs}")
        print(f"  Total Conversations: {total_conversations}")
        print(f"  Last Hour: {recent_conversations}")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"Status check failed: {e}")

if __name__ == "__main__":
    check_status()