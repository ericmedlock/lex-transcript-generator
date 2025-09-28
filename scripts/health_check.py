#!/usr/bin/env python3
"""
System Health Check - Validate all components before starting
"""

import sys
import os
import json
import requests
import psycopg2
from pathlib import Path

def check_database(db_config):
    """Test database connectivity"""
    try:
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        print("[OK] Database: Connected")
        return True
    except Exception as e:
        print(f"[FAIL] Database: {e}")
        return False

def check_llm_endpoint(endpoint):
    """Test LLM endpoint connectivity"""
    try:
        models_url = endpoint.replace('/chat/completions', '/models')
        resp = requests.get(models_url, timeout=5)
        if resp.status_code == 200:
            models = resp.json().get("data", [])
            chat_models = [m for m in models if not any(kw in m["id"].lower() 
                          for kw in ['embedding', 'embed'])]
            print(f"[OK] LLM Endpoint: {len(chat_models)} chat models available")
            return True
        else:
            print(f"[FAIL] LLM Endpoint: HTTP {resp.status_code}")
            return False
    except Exception as e:
        print(f"[FAIL] LLM Endpoint: {e}")
        return False

def check_config_files():
    """Check if config files exist"""
    configs = [
        "config/orchestrator_config.json",
        "config/node_config.json", 
        "config/bakeoff_config.json"
    ]
    
    all_good = True
    for config_file in configs:
        if Path(config_file).exists():
            print(f"[OK] Config: {config_file}")
        else:
            print(f"[FAIL] Config: {config_file} not found")
            all_good = False
    
    return all_good

def main():
    """Run comprehensive health check"""
    print("[HEALTH] System Health Check")
    print("=" * 40)
    
    all_checks_passed = True
    
    # Check config files
    if not check_config_files():
        all_checks_passed = False
    
    # Check orchestrator config
    try:
        with open("config/orchestrator_config.json", 'r') as f:
            orch_config = json.load(f)
        
        db_config = orch_config.get("db_config", {})
        if not check_database(db_config):
            all_checks_passed = False
            
    except Exception as e:
        print(f"[FAIL] Orchestrator config: {e}")
        all_checks_passed = False
    
    # Check node config
    try:
        with open("config/node_config.json", 'r') as f:
            node_config = json.load(f)
        
        llm_endpoint = node_config.get("llm_endpoint")
        if llm_endpoint and not check_llm_endpoint(llm_endpoint):
            all_checks_passed = False
            
    except Exception as e:
        print(f"[FAIL] Node config: {e}")
        all_checks_passed = False
    
    print("=" * 40)
    if all_checks_passed:
        print("[OK] All systems ready!")
        return 0
    else:
        print("[FAIL] Some checks failed - fix issues before starting")
        return 1

if __name__ == "__main__":
    sys.exit(main())