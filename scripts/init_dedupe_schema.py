#!/usr/bin/env python3
"""
Initialize deduplication database schema
"""

import psycopg2
from pathlib import Path

def main():
    db_config = {
        'host': 'EPM_DELL',
        'port': 5432,
        'database': 'calllab',
        'user': 'postgres',
        'password': 'pass'
    }
    
    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()
    
    print("Initializing deduplication schema...")
    
    # Load and execute schema
    schema_path = Path(__file__).parent.parent / "config" / "database" / "dedupe_schema.sql"
    with open(schema_path, 'r') as f:
        schema_sql = f.read()
    
    cur.execute(schema_sql)
    conn.commit()
    
    print("Deduplication schema initialized successfully")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()