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

def load_config(config_path=None):
    """Load configuration with per-hostname support"""
    hostname = socket.gethostname()
    
    # Config file search order
    search_paths = []
    if config_path:
        search_paths.append(config_path)
    search_paths.extend([
        "bakeoff_config.json",
        "config/bakeoff_config.json"
    ])
    
    for path in search_paths:
        if Path(path).exists():
            try:
                with open(path, 'r') as f:
                    all_configs = json.load(f)
                
                # Check if hostname-specific config exists
                if hostname in all_configs:
                    print(f"Loaded config for {hostname} from: {path}")
                    return all_configs[hostname]
                else:
                    # Create interactive config for this hostname
                    print(f"No config found for {hostname}, creating new config...")
                    new_config = create_interactive_bakeoff_config(hostname)
                    all_configs[hostname] = new_config
                    
                    # Save updated config
                    with open(path, 'w') as f:
                        json.dump(all_configs, f, indent=2)
                    
                    print(f"Saved config for {hostname}")
                    return new_config
                    
            except Exception as e:
                print(f"Error loading {path}: {e}")
                continue
    
    # No config file exists, create new one
    print(f"No config file found, creating new config for {hostname}...")
    new_config = create_interactive_bakeoff_config(hostname)
    config_data = {hostname: new_config}
    
    # Save to default location
    Path("config").mkdir(exist_ok=True)
    with open("config/bakeoff_config.json", 'w') as f:
        json.dump(config_data, f, indent=2)
    
    return new_config

def create_interactive_bakeoff_config(hostname):
    """Create bakeoff configuration interactively"""
    defaults = {
        "base_url": "http://localhost:1234/v1",
        "api_key": "lm-studio",
        "machine_name": hostname,
        "trials": 5,
        "conversations_per_trial": 1,
        "temperature": 0.7,
        "max_tokens": 512,
        "timeout_s": 120,
        "debug_mode": False,
        "deduplication": {
            "enabled": True,
            "similarity_threshold": 0.85,
            "max_retries": 3
        }
    }
    
    config = {}
    
    print(f"\nConfiguring bakeoff for: {hostname}")
    print("Press Enter to accept defaults, or type new value:\n")
    
    # Basic settings
    config["machine_name"] = hostname
    config["base_url"] = input(f"LLM base URL [{defaults['base_url']}]: ") or defaults["base_url"]
    config["api_key"] = input(f"API key [{defaults['api_key']}]: ") or defaults["api_key"]
    config["trials"] = int(input(f"Number of trials [{defaults['trials']}]: ") or defaults["trials"])
    config["conversations_per_trial"] = int(input(f"Conversations per trial [{defaults['conversations_per_trial']}]: ") or defaults["conversations_per_trial"])
    
    # Debug mode
    config["debug_mode"] = input(f"Debug mode [y/N]: ").lower().startswith('y')
    
    # Generation settings
    config["temperature"] = float(input(f"Temperature [{defaults['temperature']}]: ") or defaults["temperature"])
    config["max_tokens"] = int(input(f"Max tokens [{defaults['max_tokens']}]: ") or defaults["max_tokens"])
    config["timeout_s"] = int(input(f"Timeout seconds [{defaults['timeout_s']}]: ") or defaults["timeout_s"])
    
    # Deduplication
    config["deduplication"] = {
        "enabled": input(f"Enable deduplication [Y/n]: ").lower() != 'n',
        "similarity_threshold": float(input(f"Similarity threshold [{defaults['deduplication']['similarity_threshold']}]: ") or defaults["deduplication"]["similarity_threshold"]),
        "max_retries": int(input(f"Max retries [{defaults['deduplication']['max_retries']}]: ") or defaults["deduplication"]["max_retries"])
    }
    
    return config

def setup_run_directory(config, run_number):
    """Create machine-specific run directory"""
    machine_name = config.get("machine_name", "unknown")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("output") / machine_name / f"run_{run_number}_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir

def init_deduplication():
    """Initialize deduplication system"""
    try:
        from dedupe_manager import DedupeManager
        return DedupeManager()
    except Exception as e:
        print(f"Warning: Deduplication not available: {e}")
        return None

def fetch_available_models(base_url, api_key, timeout_s):
    """Fetch available models from API with enhanced error handling"""
    print(f"\n[MODEL API] Fetching models from {base_url}/models")
    
    try:
        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.get(f"{base_url}/models", headers=headers, timeout=timeout_s)
        
        print(f"[MODEL API] Response status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"[MODEL API] Error response: {response.text}")
            return []
        
        response.raise_for_status()
        data = response.json()
        
        models = [model["id"] for model in data.get("data", [])]
        print(f"[MODEL API] Successfully fetched {len(models)} models")
        
        return models
        
    except requests.exceptions.Timeout:
        print(f"[MODEL API] Timeout after {timeout_s}s - LM Studio may not be running")
        return []
    except requests.exceptions.ConnectionError:
        print(f"[MODEL API] Connection failed - check if LM Studio is running on {base_url}")
        return []
    except Exception as e:
        print(f"[MODEL API] Unexpected error: {e}")
        return []

def get_candidate_models(available_models):
    """Filter out embedding models with detailed logging"""
    chat_models = []
    embedding_keywords = ['embedding', 'embed', 'bge-', 'e5-', 'nomic-embed', 'text-embedding']
    
    print(f"\n[MODEL FILTER] Processing {len(available_models)} available models:")
    
    for model in available_models:
        model_lower = model.lower()
        is_embedding = False
        matched_keyword = None
        
        for keyword in embedding_keywords:
            if keyword in model_lower:
                is_embedding = True
                matched_keyword = keyword
                break
        
        if is_embedding:
            print(f"  ❌ SKIP: {model} (matched: '{matched_keyword}')")
        else:
            print(f"  ✅ KEEP: {model}")
            chat_models.append(model)
    
    print(f"\n[MODEL FILTER] Result: {len(chat_models)} chat models, {len(available_models) - len(chat_models)} filtered")
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

def randomize_prompt(config):
    """Generate randomized prompt from template"""
    import random
    
    scenarios = [
        "New patient scheduling first appointment",
        "Existing patient rescheduling appointment", 
        "Patient calling for urgent same-day appointment",
        "Patient scheduling follow-up after procedure",
        "Patient calling to cancel and reschedule"
    ]
    
    patient_types = [
        "Elderly patient with hearing difficulties",
        "Busy working parent with limited availability", 
        "Anxious first-time patient",
        "Regular patient who knows the system",
        "Patient with insurance questions"
    ]
    
    issues = [
        "Insurance verification needed",
        "Specific doctor preference",
        "Transportation limitations", 
        "Work schedule conflicts",
        "Multiple family members need appointments"
    ]
    
    if "prompt_template" in config:
        return config["prompt_template"].format(
            scenario=random.choice(scenarios),
            patient_type=random.choice(patient_types), 
            issue=random.choice(issues)
        )
    else:
        return config.get("prompt", "Generate a healthcare conversation")

def run_trial_with_dedupe(config, model, trial, dedupe_manager, run_number):
    """Run single trial with deduplication"""
    start_time = time.time()
    
    try:
        headers = {
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json"
        }
        
        # Generate randomized prompt
        prompt = randomize_prompt(config)
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
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
        
        # Check for duplicates using model-specific strategy
        is_duplicate = False
        duplicate_reason = "unique"
        
        if dedupe_manager and config.get("deduplication", {}).get("enabled", True):
            is_duplicate, duplicate_reason = dedupe_manager.is_duplicate(
                run_number, content, model, model_name=model
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

# Grading moved to modular grader - import it
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src', 'core'))
from conversation_grader import ConversationGrader

# GradingWorker removed - using modular grader instead

def run_trials_for_model_with_dedupe(config, model, dedupe_manager, run_number, trial_writer, grading_worker, system_info, activity_monitor):
    """Run trials for model with deduplication, retry logic, activity monitoring, and threaded grading"""
    print(f"Running model: {model}")
    
    results = []
    unique_conversations = 0
    duplicates_found = 0
    target_conversations = config["trials"] * config["conversations_per_trial"]
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
            
            # Store trial_id for later grading
            trial_id = f"{model}_{trial}_{int(time.time())}"
        else:
            duplicates_found += 1
            print(f"DUPLICATE ({result['duplicate_reason']})")
        
        # Only write trial result if unique (don't count duplicates)
        if result["unique"]:
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
    parser.add_argument("--config", help="Config file path (optional)")
    parser.add_argument("--dry-run", action="store_true", help="Test mode")
    
    args = parser.parse_args()
    
    # Load config with per-hostname support
    config = load_config(args.config)
    
    # Initialize deduplication
    dedupe_manager = init_deduplication()
    if not dedupe_manager:
        print("ERROR: Could not initialize deduplication system")
        return 1
    
    # Create per-node deduplication run
    available_models = fetch_available_models(config["base_url"], config["api_key"], config["timeout_s"])
    print(f"Available models from API: {available_models}")
    candidate_models = get_candidate_models(available_models)
    print(f"Filtered candidate models: {candidate_models}")
    
    # Apply models filter only in debug mode
    if config.get("debug_mode", False) and "models_filter" in config and config["models_filter"]:
        candidate_models = [m for m in candidate_models if m in config["models_filter"]]
    
    if not candidate_models:
        print("ERROR: No models available")
        return 1
    
    target_conversations = len(candidate_models) * config["trials"] * config["conversations_per_trial"]
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
    
    # Open CSV files with machine name prefix
    machine_name = config.get("machine_name", "unknown")
    summary_csv = output_dir / f"{machine_name}_bakeoff_summary.csv"
    trials_csv = output_dir / f"{machine_name}_bakeoff_trials.csv"
    
    # Open all CSV files (keep open for threaded grading)
    trials_file = open(trials_csv, 'w', newline='', encoding='utf-8')
    summary_file = open(summary_csv, 'w', newline='', encoding='utf-8')
    gan_csv = output_dir / f"{machine_name}_bakeoff_gan.csv"
    gan_file = open(gan_csv, 'w', newline='', encoding='utf-8')
    
    trial_writer = csv.writer(trials_file)
    summary_writer = csv.writer(summary_file)
    gan_writer = csv.writer(gan_file)
    
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
    
    gan_writer.writerow([
        "trial_id", "timestamp", "model", "trial", "realness_score", "coherence_score",
        "naturalness_score", "overall_score", "brief_feedback", "grading_error"
    ])
    
    # Initialize grader for post-processing
    grader = ConversationGrader()
    
    try:
        # Run trials for each model (generation only)
        for model in candidate_models:
            results, unique_count, duplicate_count = run_trials_for_model_with_dedupe(
                config, model, dedupe_manager, run_number, trial_writer, None, system_info, activity_monitor
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
    
        
        # Now grade using CSV files after all generation is complete
        print("\n[MAIN] Starting grading phase...")
        csv_files = [trials_csv]
        gan_output = output_dir / f"{machine_name}_bakeoff_gan.csv"
        grader.grade_csv_files(csv_files, gan_output)
        
    finally:
        # Grading complete
        # Close all files
        trials_file.close()
        summary_file.close()
        gan_file.close()
    
    # Close deduplication run
    dedupe_manager.close_run(run_number)
    stats = dedupe_manager.get_run_stats(run_number)
    
    print(f"\nRun completed:")
    print(f"  Unique conversations stored: {stats['stored']}")
    print(f"  Target: {stats['target']}")
    print(f"  Results saved to: {output_dir}")
    print(f"  Files: {machine_name}_bakeoff_summary.csv, {machine_name}_bakeoff_trials.csv, {machine_name}_bakeoff_gan.csv")
    
    return 0

if __name__ == "__main__":
    exit(main())