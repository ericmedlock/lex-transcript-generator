#!/usr/bin/env python3
"""
Recreate RAG tables with correct vector dimensions
"""

import psycopg2

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
    
    # Drop existing tables
    print("Dropping existing RAG tables...")
    cur.execute("DROP TABLE IF EXISTS document_chunks CASCADE")
    cur.execute("DROP TABLE IF EXISTS rag_sources CASCADE")
    
    # Recreate with correct dimensions
    print("Creating RAG tables with 768 dimensions...")
    
    # Read and execute schema
    with open('config/database/rag_schema.sql', 'r') as f:
        schema_sql = f.read()
    
    cur.execute(schema_sql)
    conn.commit()
    
    print("RAG tables recreated successfully")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()