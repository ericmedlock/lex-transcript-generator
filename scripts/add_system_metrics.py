#!/usr/bin/env python3
"""
Add system_metrics column to nodes table
"""

import psycopg2

def add_system_metrics_column():
    """Add system_metrics column to nodes table"""
    
    db_config = {
        'host': '192.168.68.60',
        'port': 5432,
        'database': 'calllab',
        'user': 'postgres',
        'password': 'pass'
    }
    
    try:
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()
        
        # Check if column already exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name = 'nodes' AND column_name = 'system_metrics'
            )
        """)
        
        column_exists = cur.fetchone()[0]
        
        if not column_exists:
            print("Adding system_metrics column to nodes table...")
            cur.execute("ALTER TABLE nodes ADD COLUMN system_metrics JSONB")
            conn.commit()
            print("[OK] system_metrics column added successfully")
        else:
            print("[INFO] system_metrics column already exists")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"[ERROR] Error adding column: {e}")

if __name__ == "__main__":
    add_system_metrics_column()