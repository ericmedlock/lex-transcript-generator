#!/usr/bin/env python3
"""
Model Bakeoff with Deduplication - Enhanced version with run management and organized output
"""

import json
import csv
import time
import subprocess
import argparse
import os
import platform
import socket
import threading
import queue
import sys
from datetime import datetime
from pathlib import Path
import requests
from openai import OpenAI
import os

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src', 'core'))
from activity_monitor import ActivityMonitor

def load_config(config_path):
    """Load configuration with defaults"""
    defaults = {
        "base_url": "http://localhost:1234/v1",
        "api_key": "lm-studio",
        "machine_name": socket.gethostname(),
        "trials": 5,
        "conversations_per_trial": 1,
        "temperature": 0.7,
        "max_tokens": 512,
        "timeout_s": 120,
        "unload_between_models": False,
        "prompt": "Generate a realistic healthcare appointment conversation",
        "deduplication": {
            "enabled": True,
            "similarity_threshold": 0.85,
            "max_retries": 3,
            "output_directory": "output/tool_runs"
        }
    }
    
    if not Path(config_path).exists():
        print(f"Config file {config_path} not found, using defaults")
        return defaults
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Merge with defaults
        for key, value in defaults.items():
            if key not in config:
                config[key] = value
        
        return config
    except Exception as e:
        print(f"Error loading config: {e}")
        return defaults

def setup_run_directory(config, run_number):
    """Create run-specific output directory"""
    base_dir = config.get("deduplication", {}).get("output_directory", "output/tool_runs")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(base_dir) / f"run_{run_number}_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir

def init_deduplication(config):
    """Initialize deduplication system"""
    try:
        from dedupe_manager import DedupeManager
        dedupe_manager = DedupeManager()
        
        # Setup database schema
        conn = dedupe_manager.get_db()
        cur = conn.cursor()
        
        # Load and execute dedupe schema
        schema_path = Path(__file__).parent.parent / "config" / "database" / "dedupe_schema.sql"
        if schema_path.exists():
            with open(schema_path, 'r') as f:
                cur.execute(f.read())
            conn.commit()
        
        cur.close()
        conn.close()
        
        return dedupe_manager
    except Exception as e:
        print(f"Warning: Deduplication not available: {e}")
        return None

def fetch_available_models(base_url, api_key, timeout_s):
    """Fetch available models from API"""
    try:
        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.get(f"{base_url}/models", headers=headers, timeout=timeout_s)
        response.raise_for_status()
        
        data = response.json()
        return [model["id"] for model in data.get("data", [])]
    except Exception as e:
        print(f"Error fetching models: {e}")
        return []

def get_candidate_models(available_models):
    """Filter out embedding models"""
    chat_models = []
    for model in available_models:
        model_lower = model.lower()
        if any(skip in model_lower for skip in ['embedding', 'embed', 'bge-', 'e5-', 'nomic-embed']):
            print(f"Skipping embedding model: {model}")
            continue
        chat_models.append(model)
    return chat_models

def detect_system_info():
    """Detect system and GPU information"""
    system_info = {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "processor": platform.processor(),
        "gpu_info": "Unknown",
        "gpu_memory": "Unknown"
    }
    
    # Try to detect GPU using nvidia-smi
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().split('\n')
            gpu_data = lines[0].split(', ')
            if len(gpu_data) >= 2:
                system_info["gpu_info"] = gpu_data[0].strip()
                system_info["gpu_memory"] = f"{gpu_data[1].strip()}MB"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    return system_info

def run_trial_with_dedupe(config, model, trial, dedupe_manager, run_number):
    """Run single trial with deduplication"""
    start_time = time.time()
    
    try:
        headers = {
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": config["prompt"]}],
            "temperature": config["temperature"],
            "max_tokens": config["max_tokens"]
        }
        
        response = requests.post(
            f"{config['base_url']}/chat/completions",
            headers=headers,
            json=payload,
            timeout=config["timeout_s"]
        )
        
        latency_s = time.time() - start_time
        
        if response.status_code != 200:
            return {
                "error": f"HTTP {response.status_code}",
                "latency_s": latency_s,
                "unique": False,
                "duplicate_reason": "api_error"
            }
        
        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        # Check for duplicates
        is_duplicate = False
        duplicate_reason = "unique"
        
        if dedupe_manager and config.get("deduplication", {}).get("enabled", True):
            similarity_threshold = config.get("deduplication", {}).get("similarity_threshold", 0.85)
            hash_only = config.get("deduplication", {}).get("hash_only", False)
            is_duplicate, duplicate_reason = dedupe_manager.is_duplicate(
                run_number, content, model, similarity_threshold, hash_only
            )
        
        usage = data.get("usage", {})
        completion_tokens = usage.get("completion_tokens", len(content.split()))
        tokens_per_sec = completion_tokens / latency_s if latency_s > 0 else 0
        
        return {
            "error": None,
            "latency_s": latency_s,
            "completion_tokens": completion_tokens,
            "tokens_per_sec": tokens_per_sec,
            "content": content,
            "unique": not is_duplicate,
            "duplicate_reason": duplicate_reason
        }
        
    except Exception as e:
        latency_s = time.time() - start_time
        return {
            "error": str(e),
            "latency_s": latency_s,
            "unique": False,
            "duplicate_reason": "error"
        }

def grade_conversation_with_openai(conversation_text, trial_id):
    """Grade conversation using OpenAI API"""
    try:
        openai_key = os.getenv('OPENAI_API_KEY')
        if not openai_key:
            return {
                "realness_score": None,
                "coherence_score": None, 
                "naturalness_score": None,
                "overall_score": None,
                "grading_error": "No OpenAI API key"
            }
        
        client = OpenAI(api_key=openai_key)
        
        grading_prompt = f"""Grade this AI-generated conversation on a scale of 1-10 for each metric:

1. REALNESS: How realistic and believable is this conversation? (1=obviously AI, 10=indistinguishable from human)
2. COHERENCE: How well does the conversation flow logically? (1=nonsensical, 10=perfect flow)
3. NATURALNESS: How natural do the speech patterns sound? (1=robotic, 10=completely natural)
4. OVERALL: Overall quality for training chatbot systems (1=unusable, 10=excellent training data)

Conversation to grade:
{conversation_text[:2000]}...

Respond ONLY with JSON format:
{{
  "realness_score": X,
  "coherence_score": X,
  "naturalness_score": X,
  "overall_score": X,
  "brief_feedback": "one sentence explanation"
}}"""
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": grading_prompt}],
            temperature=0.1,
            max_tokens=200
        )
        
        result_text = response.choices[0].message.content.strip()
        
        try:
            grades = json.loads(result_text)
            grades["grading_error"] = None
            return grades
        except json.JSONDecodeError:
            return {
                "realness_score": None,
                "coherence_score": None,
                "naturalness_score": None, 
                "overall_score": None,
                "grading_error": f"Invalid JSON: {result_text[:100]}"
            }
            
    except Exception as e:
        return {
            "realness_score": None,
            "coherence_score": None,
            "naturalness_score": None,
            "overall_score": None,
            "grading_error": str(e)
        }

def run_trials_for_model_with_dedupe(config, model, dedupe_manager, run_number, trial_writer, gan_writer, system_info, activity_monitor):
    """Run trials for model with deduplication, retry logic, activity monitoring, and grading"""
    print(f"Running model: {model}")
    
    results = []
    unique_conversations = 0
    duplicates_found = 0
    target_conversations = config["conversations_per_trial"]
    max_retries = config.get("deduplication", {}).get("max_retries", 3)
    
    trial = 1
    while unique_conversations < target_conversations and trial <= target_conversations + max_retries:
        # Check activity and throttle if needed
        limits = activity_monitor.get_resource_limits()
        mode = activity_monitor.get_activity_mode()
        
        if mode in ["gaming", "thermal_throttle"]:
            print(f"  Pausing due to {mode}, waiting {limits['delay']}s...")
            time.sleep(limits["delay"])
            continue
        
        if activity_monitor.should_throttle():
            print(f"  Throttling due to high resource usage, waiting {limits['delay']}s...")
            time.sleep(limits["delay"])
            continue
        
        print(f"  Trial {trial} (need {target_conversations - unique_conversations} more unique, mode: {mode})...", end=" ")
        
        result = run_trial_with_dedupe(config, model, trial, dedupe_manager, run_number)
        
        if result["error"]:
            print(f"ERROR: {result['error']}")
        elif result["unique"]:
            unique_conversations += 1
            print(f"UNIQUE ({unique_conversations}/{target_conversations})")
            
            # Grade the unique conversation
            conversation_content = result.get("content", "")
            trial_id = f"{model}_{trial}_{int(time.time())}"
            
            print(f"    Grading conversation...")
            grades = grade_conversation_with_openai(conversation_content, trial_id)
            
            if grades.get("grading_error"):
                print(f"    Grading error: {grades['grading_error']}")
            else:
                print(f"    Grades: R={grades.get('realness_score')}, O={grades.get('overall_score')}")
            
            # Write grading result
            gan_writer.writerow([
                trial_id,
                datetime.now().isoformat(),
                model,
                trial,
                grades.get("realness_score"),
                grades.get("coherence_score"),
                grades.get("naturalness_score"),
                grades.get("overall_score"),
                grades.get("brief_feedback", ""),
                grades.get("grading_error", "")
            ])
        else:
            duplicates_found += 1
            print(f"DUPLICATE ({result['duplicate_reason']})")
        
        # Write trial result
        trial_id = f"{model}_{trial}_{int(time.time())}"
        timestamp = datetime.now().isoformat()
        
        trial_writer.writerow([
            trial_id,
            timestamp,
            config["machine_name"],
            system_info["gpu_info"],
            system_info["gpu_memory"],
            system_info["platform"],
            model,
            trial,
            result["latency_s"],
            result.get("completion_tokens", 0),
            result.get("tokens_per_sec", 0),
            result["unique"],
            result["duplicate_reason"],
            result.get("content", "")[:500] if result.get("content") else ""
        ])
        
        results.append(result)
        trial += 1
    
    print(f"  Completed: {unique_conversations} unique, {duplicates_found} duplicates")
    return results, unique_conversations, duplicates_found

def main():
    parser = argparse.ArgumentParser(description="Model bakeoff with deduplication")
    parser.add_argument("--config", default="config.json", help="Config file path")
    parser.add_argument("--dry-run", action="store_true", help="Test mode")
    
    args = parser.parse_args()
    
    # Load config
    config = load_config(args.config)
    
    # Initialize deduplication
    dedupe_manager = init_deduplication(config)
    if not dedupe_manager:
        print("ERROR: Could not initialize deduplication system")
        return 1
    
    # Create per-node deduplication run
    available_models = fetch_available_models(config["base_url"], config["api_key"], config["timeout_s"])
    candidate_models = get_candidate_models(available_models)
    
    # Apply models filter only in debug mode
    if config.get("debug_mode", False) and "models_filter" in config and config["models_filter"]:
        candidate_models = [m for m in candidate_models if m in config["models_filter"]]
    
    if not candidate_models:
        print("ERROR: No models available")
        return 1
    
    target_conversations = len(candidate_models) * config["conversations_per_trial"]
    similarity_threshold = config.get("deduplication", {}).get("similarity_threshold", 0.85)
    
    # Use machine-specific run for bakeoff testing
    machine_name = config.get("machine_name", "unknown")
    debug_mode = config.get("debug_mode", False)
    run_prefix = f"debug_{machine_name}" if debug_mode else f"bakeoff_{machine_name}"
    run_id, run_number = dedupe_manager.get_or_create_run(
        target_conversations, 
        similarity_threshold,
        run_prefix=run_prefix
    )
    print(f"Using per-node deduplication run: {run_number} ({machine_name})")
    
    # Setup output directory
    output_dir = setup_run_directory(config, run_number)
    print(f"Output directory: {output_dir}")
    
    # Detect system info and initialize activity monitor
    system_info = detect_system_info()
    activity_monitor = ActivityMonitor(config)
    
    print(f"Machine: {config['machine_name']}")
    print(f"GPU: {system_info['gpu_info']} ({system_info['gpu_memory']})")
    print(f"Models: {candidate_models}")
    print(f"Target conversations: {target_conversations}")
    print()
    
    # Open CSV files
    summary_csv = output_dir / "bakeoff_summary.csv"
    trials_csv = output_dir / "bakeoff_trials.csv"
    
    with open(trials_csv, 'w', newline='', encoding='utf-8') as trials_file, \
         open(summary_csv, 'w', newline='', encoding='utf-8') as summary_file:
        
        trial_writer = csv.writer(trials_file)
        summary_writer = csv.writer(summary_file)
        
        # Write headers
        trial_writer.writerow([
            "trial_id", "timestamp", "machine_name", "gpu_info", "gpu_memory", "platform",
            "model", "trial", "latency_s", "completion_tokens", "tokens_per_sec", 
            "unique", "duplicate_reason", "sample_output"
        ])
        
        summary_writer.writerow([
            "timestamp", "machine_name", "gpu_info", "gpu_memory", "platform",
            "model", "trials_run", "unique_conversations", "duplicates_found", 
            "duplicate_rate", "avg_latency_s", "avg_tokens_per_sec"
        ])
        
        # Open GAN CSV file
        gan_csv = output_dir / "bakeoff_gan.csv"
        with open(gan_csv, 'w', newline='', encoding='utf-8') as gan_file:
            gan_writer = csv.writer(gan_file)
            
            # Write GAN header
            gan_writer.writerow([
                "trial_id", "timestamp", "model", "trial", "realness_score", "coherence_score",
                "naturalness_score", "overall_score", "brief_feedback", "grading_error"
            ])
            
            # Run trials for each model
            for model in candidate_models:
                results, unique_count, duplicate_count = run_trials_for_model_with_dedupe(
                    config, model, dedupe_manager, run_number, trial_writer, gan_writer, system_info, activity_monitor
                )
            
            # Calculate summary
            valid_results = [r for r in results if not r["error"] and r["unique"]]
            
            if valid_results:
                avg_latency = sum(r["latency_s"] for r in valid_results) / len(valid_results)
                avg_tokens_per_sec = sum(r["tokens_per_sec"] for r in valid_results) / len(valid_results)
            else:
                avg_latency = 0
                avg_tokens_per_sec = 0
            
                duplicate_rate = (duplicate_count / (unique_count + duplicate_count) * 100) if (unique_count + duplicate_count) > 0 else 0
                
                # Write summary
                summary_writer.writerow([
                    datetime.now().isoformat(),
                    config["machine_name"],
                    system_info["gpu_info"],
                    system_info["gpu_memory"],
                    system_info["platform"],
                    model,
                    len(results),
                    unique_count,
                    duplicate_count,
                    duplicate_rate,
                    avg_latency,
                    avg_tokens_per_sec
                ])
    
    # Close deduplication run
    dedupe_manager.close_run(run_number)
    stats = dedupe_manager.get_run_stats(run_number)
    
    print(f"\nRun completed:")
    print(f"  Unique conversations stored: {stats['stored']}")
    print(f"  Target: {stats['target']}")
    print(f"  Results saved to: {output_dir}")
    print(f"  Files: bakeoff_summary.csv, bakeoff_trials.csv, bakeoff_gan.csv")
    
    return 0

if __name__ == "__main__":
    exit(main())