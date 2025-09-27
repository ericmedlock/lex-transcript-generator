#!/usr/bin/env python3
"""
Database setup and management script
"""

import sqlite3
import json
import uuid
from pathlib import Path

DB_PATH = "data/transcript_platform.db"
SCHEMA_PATH = "config/database/schema.sql"

def init_database():
    """Initialize database with schema and sample data"""
    
    # Create data directory
    Path("data").mkdir(exist_ok=True)
    
    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    
    # Read and execute schema
    with open(SCHEMA_PATH, 'r') as f:
        schema = f.read()
    
    conn.executescript(schema)
    
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
        conn.execute(
            "INSERT INTO scenarios (name, domain, template) VALUES (?, ?, ?)",
            (name, domain, template)
        )
    
    # Add master node
    master_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO nodes (id, hostname, node_type, status, capabilities) VALUES (?, ?, ?, ?, ?)",
        (master_id, "master-node", "master", "online", json.dumps(["orchestration", "web_ui"]))
    )
    
    conn.commit()
    conn.close()
    
    print(f"✅ Database initialized: {DB_PATH}")
    print(f"📊 Added {len(scenarios)} scenarios")
    print("🚀 Ready to start nodes")

def reset_database():
    """Drop and recreate database"""
    if Path(DB_PATH).exists():
        Path(DB_PATH).unlink()
        print("🗑️  Deleted existing database")
    
    init_database()

def show_status():
    """Show database status"""
    if not Path(DB_PATH).exists():
        print("❌ Database not found. Run: python scripts/db_setup.py init")
        return
    
    conn = sqlite3.connect(DB_PATH)
    
    # Count records
    tables = ['nodes', 'models', 'scenarios', 'jobs', 'conversations']
    for table in tables:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table}: {count} records")
    
    conn.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python scripts/db_setup.py init     # Initialize database")
        print("  python scripts/db_setup.py reset    # Reset database")
        print("  python scripts/db_setup.py status   # Show status")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "init":
        init_database()
    elif command == "reset":
        reset_database()
    elif command == "status":
        show_status()
    else:
        print(f"Unknown command: {command}")