#!/usr/bin/env python3
"""Reset system for a new run"""

import psycopg2

def reset_system():
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
        
        # Clear all related tables in correct order
        cur.execute("DELETE FROM conversation_grades")
        deleted_grades = cur.rowcount
        
        cur.execute("DELETE FROM conversations")
        deleted_conversations = cur.rowcount
        
        cur.execute("DELETE FROM jobs")
        deleted_jobs = cur.rowcount
        
        # Reset master nodes to offline so new orchestrator can start
        cur.execute("UPDATE nodes SET status = 'offline' WHERE node_type = 'master'")
        
        conn.commit()
        print(f"Deleted {deleted_grades} conversation grades")
        print(f"Deleted {deleted_conversations} conversations")
        print(f"Deleted {deleted_jobs} jobs")
        print("Reset master nodes to offline")
        print("System cleared and ready for new run")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    reset_system()