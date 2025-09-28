#!/usr/bin/env python3
"""Quick check of orchestrator status"""

import psycopg2
import json

def check_status():
    db_config = {
        'host': 'EPM_DELL',
        'port': 5432,
        'database': 'calllab',
        'user': 'postgres',
        'password': 'pass'
    }
    
    try:
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()
        
        # Check scenarios
        cur.execute("SELECT COUNT(*) FROM scenarios")
        scenario_count = cur.fetchone()[0]
        print(f"Scenarios: {scenario_count}")
        
        if scenario_count > 0:
            cur.execute("SELECT id, name FROM scenarios LIMIT 3")
            scenarios = cur.fetchall()
            for s_id, name in scenarios:
                print(f"  - {name} ({s_id[:8]})")
        
        # Check jobs
        cur.execute("SELECT COUNT(*), status FROM jobs GROUP BY status")
        job_status = cur.fetchall()
        print(f"Jobs by status: {job_status}")
        
        # Check nodes
        cur.execute("SELECT hostname, node_type, status, last_seen FROM nodes ORDER BY last_seen DESC")
        nodes = cur.fetchall()
        print(f"Nodes:")
        for hostname, node_type, status, last_seen in nodes:
            print(f"  - {hostname} ({node_type}): {status} - {last_seen}")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_status()