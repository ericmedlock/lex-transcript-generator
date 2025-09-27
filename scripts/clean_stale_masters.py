#!/usr/bin/env python3
"""
Clean stale master node records
"""

import psycopg2

def main():
    # Try different connection methods
    db_configs = [
        {'host': 'localhost', 'port': 5432, 'database': 'calllab', 'user': 'postgres', 'password': 'pass'},
        {'host': '127.0.0.1', 'port': 5432, 'database': 'calllab', 'user': 'postgres', 'password': 'pass'},
        {'host': 'EPM_DELL', 'port': 5432, 'database': 'calllab', 'user': 'postgres', 'password': 'pass'}
    ]
    
    for config in db_configs:
        try:
            print(f"Trying connection to {config['host']}...")
            conn = psycopg2.connect(**config)
            cur = conn.cursor()
            
            # Show current master records
            cur.execute("SELECT hostname, node_type, status FROM nodes WHERE node_type='master'")
            masters = cur.fetchall()
            print(f"Current masters: {masters}")
            
            # Delete all master records
            cur.execute("DELETE FROM nodes WHERE node_type='master'")
            deleted_count = cur.rowcount
            conn.commit()
            
            print(f"Deleted {deleted_count} master records")
            
            cur.close()
            conn.close()
            return
            
        except Exception as e:
            print(f"Failed to connect to {config['host']}: {e}")
            continue
    
    print("Could not connect to any database")

if __name__ == "__main__":
    main()