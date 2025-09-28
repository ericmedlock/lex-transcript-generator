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
    
    print("Cleaning transaction tables...")
    for table in tables_to_clean:
        try:
            cur.execute(f"TRUNCATE TABLE {table} CASCADE")
            print(f"✓ Cleaned {table}")
        except Exception as e:
            print(f"⚠ Could not clean {table}: {e}")
    
    conn.commit()
    cur.close()
    conn.close()
    print("Database cleaned for fresh run")

if __name__ == "__main__":
    clean_tables()