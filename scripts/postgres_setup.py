#!/usr/bin/env python3
"""
PostgreSQL setup and management script
"""

import psycopg2
import json
import uuid
from pathlib import Path

DB_CONFIG = {
    'host': 'EPM_DELL',
    'port': 5432,
    'database': 'calllab',
    'user': 'postgres',
    'password': 'pass'
}

SCHEMA_PATH = "config/database/postgres_schema.sql"

def get_connection():
    """Get PostgreSQL connection"""
    return psycopg2.connect(**DB_CONFIG)

def init_database():
    """Initialize PostgreSQL database with schema and sample data"""
    
    conn = get_connection()
    cur = conn.cursor()
    
    # Read and execute schema
    with open(SCHEMA_PATH, 'r') as f:
        schema = f.read()
    
    cur.execute(schema)
    
    # Add sample scenarios
    scenarios = [
        ("Healthcare Appointment Scheduling", "healthcare", 
         "Generate a medical appointment scheduling conversation between a patient and receptionist."),
        ("Healthcare Appointment Cancellation", "healthcare",
         "Generate a conversation where a patient cancels their medical appointment."),
        ("Healthcare Insurance Verification", "healthcare",
         "Generate a conversation about verifying patient insurance information."),
        ("Pizza Order Placement", "retail",
         "Generate a conversation where a customer orders pizza over the phone."),
        ("Cable Service Cancellation", "telecom",
         "Generate a conversation where a customer cancels their cable service.")
    ]
    
    for name, domain, template in scenarios:
        cur.execute(
            "INSERT INTO scenarios (name, domain, template) VALUES (%s, %s, %s)",
            (name, domain, template)
        )
    
    # Add master node
    master_id = str(uuid.uuid4())
    cur.execute(
        "INSERT INTO nodes (id, hostname, node_type, status, capabilities) VALUES (%s, %s, %s, %s, %s)",
        (master_id, "master-node", "master", "online", json.dumps(["orchestration", "web_ui"]))
    )
    
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"✅ PostgreSQL database initialized: {DB_CONFIG['database']}")
    print(f"📊 Added {len(scenarios)} scenarios")
    print("🚀 Ready to start nodes")

def show_status():
    """Show database status"""
    conn = get_connection()
    cur = conn.cursor()
    
    # Count records
    tables = ['nodes', 'models', 'scenarios', 'jobs', 'conversations']
    for table in tables:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        print(f"{table}: {count} records")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python scripts/postgres_setup.py init     # Initialize database")
        print("  python scripts/postgres_setup.py status   # Show status")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "init":
        init_database()
    elif command == "status":
        show_status()
    else:
        print(f"Unknown command: {command}")