#!/usr/bin/env python3
"""
Setup RAG database schema
"""

import psycopg2
from pathlib import Path

def setup_rag_schema():
    """Setup RAG database schema"""
    db_config = {
        'host': 'EPM_DELL',
        'port': 5432,
        'database': 'calllab',
        'user': 'postgres',
        'password': 'pass'
    }
    
    # Read schema file
    schema_file = Path("config/database/rag_schema.sql")
    if not schema_file.exists():
        print(f"Schema file not found: {schema_file}")
        return False
    
    with open(schema_file, 'r') as f:
        schema_sql = f.read()
    
    try:
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()
        
        print("Setting up RAG schema...")
        cur.execute(schema_sql)
        
        conn.commit()
        cur.close()
        conn.close()
        
        print("RAG schema setup complete!")
        return True
        
    except Exception as e:
        print(f"Error setting up RAG schema: {e}")
        return False

if __name__ == "__main__":
    setup_rag_schema()