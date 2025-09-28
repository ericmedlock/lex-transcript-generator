#!/usr/bin/env python3
"""
Clean all transaction tables for fresh run
"""
import psycopg2
import json
from pathlib import Path

def load_db_config():
    """Load database configuration"""
    config_paths = [
        "config/orchestrator_config.json",
        "config/node_config.json"
    ]
    
    for path in config_paths:
        if Path(path).exists():
            with open(path, 'r') as f:
                config = json.load(f)
                if "db_config" in config:
                    return config["db_config"]
                # Check hostname configs
                for hostname_config in config.values():
                    if isinstance(hostname_config, dict) and "db_config" in hostname_config:
                        return hostname_config["db_config"]
    
    return {
        "host": "EPM_DELL",
        "port": 5432,
        "database": "calllab",
        "user": "postgres",
        "password": "pass"
    }

def clean_tables():
    """Truncate all transaction tables"""
    db_config = load_db_config()
    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()
    
    tables_to_clean = [
        "conversations",
        "conversation_grades", 
        "jobs",
        "nodes",
        "dedupe_runs",
        "dedupe_hashes"
    ]
    
    # Reset run counter
    try:
        cur.execute("UPDATE run_counter SET current_run = 0")
        print("[OK] Reset run counter")
    except Exception as e:
        print(f"[WARN] Could not reset run counter: {e}")
    
    print("Cleaning transaction tables...")
    
    # Reset run counter to 0
    try:
        cur.execute("UPDATE run_counter SET current_run = 0")
        print("[OK] Reset run counter to 0")
    except Exception as e:
        print(f"[WARN] Could not reset run counter: {e}")
    
    # Delete in correct order (conversations first, then jobs)
    try:
        cur.execute("DELETE FROM conversations")
        cur.execute("DELETE FROM conversation_grades")
        cur.execute("DELETE FROM jobs")
        cur.execute("DELETE FROM nodes WHERE node_type != 'master'")
        print(f"[OK] Force deleted all data")
    except Exception as e:
        print(f"[WARN] Could not force delete: {e}")
    
    # Truncate remaining tables
    remaining_tables = ["dedupe_runs"]
    for table in remaining_tables:
        try:
            cur.execute(f"TRUNCATE TABLE {table} CASCADE")
            print(f"[OK] Cleaned {table}")
        except Exception as e:
            print(f"[WARN] Could not clean {table}: {e}")
    
    conn.commit()
    cur.close()
    conn.close()
    print("Database cleaned for fresh run")

if __name__ == "__main__":
    clean_tables()