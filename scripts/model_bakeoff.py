#!/usr/bin/env python3
"""
Model Bakeoff - Benchmark multiple models for conversation generation
"""

import json
import csv
import time
import subprocess
import argparse
import os
import platform
import socket
from datetime import datetime
from pathlib import Path
import requests
from openai import OpenAI

def load_config(config_path):
    """Load configuration with defaults"""
    defaults = {
        "base_url": "http://localhost:1234/v1",
        "api_key": "lm-studio",
        "machine_name": socket.gethostname(),
        "trials": 5,
        "temperature": 0.7,
        "max_tokens": 512,
        "timeout_s": 120,
        "unload_between_models": False,
        "prompt": "Summarize the Fermi paradox in 3 bullets."
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
        
        # Override with env vars
        if "OPENAI_API_KEY" in os.environ:
            config["api_key"] = os.environ["OPENAI_API_KEY"]
        
        return config
    except Exception as e:
        print(f"Error loading config: {e}")
        return defaults

def fetch_available_models(base_url, api_key, timeout_s):
    """Fetch available models from API"""
    try:
        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.get(f"{base_url}/models", headers=headers, timeout=timeout_s)
        response.raise_for_status()
        
        data = response.json()
        return [model["id"] for model in data.get("data", [])]
    except Exception as e:
        print(f"Error fetching models from {base_url}/models: {e}")
        return []

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
    
    # Fallback: try wmic on Windows
    if system_info["gpu_info"] == "Unknown" and platform.system() == "Windows":
        try:
            result = subprocess.run(
                ["wmic", "path", "win32_VideoController", "get", "name", "/format:csv"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                lines = [line.strip() for line in result.stdout.split('\n') if line.strip()]
                for line in lines[1:]:  # Skip header
                    parts = line.split(',')
                    if len(parts) > 1 and parts[1].strip():
                        system_info["gpu_info"] = parts[1].strip()
                        break
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
    
    return system_info

def get_candidate_models(available_models):
    """Return only chat-capable models (filter out embeddings)"""
    # Filter out embedding models
    chat_models = []
    for model in available_models:
        model_lower = model.lower()
        if any(skip in model_lower for skip in ['embedding', 'embed', 'bge-', 'e5-', 'nomic-embed']):
            print(f"Skipping embedding model: {model}")
            continue
        chat_models.append(model)
    return chat_models

def estimate_tokens(text):
    """Simple token estimation"""
    return len(text.split())

def grade_conversation_with_openai(conversation_text, trial_id):
    """Grade conversation using OpenAI API"""
    try:
        # Check for OpenAI API key
        openai_key = os.getenv('OPENAI_API_KEY')
        if not openai_key:
            print("WARNING: OPENAI_API_KEY not found in environment variables")
            return {
                "trial_id": trial_id,
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
        
        # Parse JSON response
        try:
            grades = json.loads(result_text)
            grades["trial_id"] = trial_id
            grades["grading_error"] = None
            return grades
        except json.JSONDecodeError:
            return {
                "trial_id": trial_id,
                "realness_score": None,
                "coherence_score": None,
                "naturalness_score": None, 
                "overall_score": None,
                "grading_error": f"Invalid JSON: {result_text[:100]}"
            }
            
    except Exception as e:
        return {
            "trial_id": trial_id,
            "realness_score": None,
            "coherence_score": None,
            "naturalness_score": None,
            "overall_score": None,
            "grading_error": str(e)
        }

def run_trial(base_url, api_key, model, prompt, temperature, max_tokens, timeout_s):
    """Run single trial and return results"""
    start_time = time.time()
    
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        response = requests.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=timeout_s
        )
        
        latency_s = time.time() - start_time
        
        if response.status_code != 200:
            return {
                "error": f"HTTP {response.status_code}",
                "latency_s": latency_s,
                "completion_tokens": 0,
                "tokens_per_sec": 0,
                "sample_output": ""
            }
        
        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        # Get completion tokens
        usage = data.get("usage", {})
        completion_tokens = usage.get("completion_tokens", estimate_tokens(content))
        
        tokens_per_sec = completion_tokens / latency_s if latency_s > 0 else 0
        
        return {
            "error": None,
            "latency_s": latency_s,
            "completion_tokens": completion_tokens,
            "tokens_per_sec": tokens_per_sec,
            "sample_output": content[:500],
            "full_output": content
        }
        
    except Exception as e:
        latency_s = time.time() - start_time
        return {
            "error": str(e),
            "latency_s": latency_s,
            "completion_tokens": 0,
            "tokens_per_sec": 0,
            "sample_output": ""
        }

def unload_models():
    """Try to unload models using CLI"""
    try:
        result = subprocess.run(
            ["lms", "unload", "--all"],
            capture_output=True,
            text=True,
            timeout=30
        )
        return {
            "code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except FileNotFoundError:
        return {
            "code": -1,
            "stdout": "",
            "stderr": "lms command not found"
        }
    except Exception as e:
        return {
            "code": -1,
            "stdout": "",
            "stderr": str(e)
        }

def run_trials_for_model(config, model, trial_writer, gan_writer, system_info):
    """Run all trials for a single model"""
    print(f"Running model: {model}")
    
    results = []
    
    for trial in range(1, config["trials"] + 1):
        print(f"  Trial {trial}/{config['trials']}")
        
        result = run_trial(
            config["base_url"],
            config["api_key"],
            model,
            config["prompt"],
            config["temperature"],
            config["max_tokens"],
            config["timeout_s"]
        )
        
        # Generate unique trial ID for linking
        trial_id = f"{model}_{trial}_{int(time.time())}"
        
        # Write trial row
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
            result["completion_tokens"],
            result["tokens_per_sec"],
            result["sample_output"]
        ])
        
        if result["error"]:
            print(f"    ERROR: {result['error']}")
        else:
            print(f"    {result['latency_s']:.2f}s, {result['tokens_per_sec']:.1f} tok/s")
            
            # Grade with OpenAI if we have output
            if result.get("full_output"):
                print(f"    Grading with OpenAI...")
                grades = grade_conversation_with_openai(result["full_output"], trial_id)
                
                # Write GAN grading row
                gan_writer.writerow([
                    trial_id,
                    timestamp,
                    model,
                    trial,
                    grades.get("realness_score"),
                    grades.get("coherence_score"),
                    grades.get("naturalness_score"),
                    grades.get("overall_score"),
                    grades.get("brief_feedback", ""),
                    grades.get("grading_error", "")
                ])
                
                if grades.get("grading_error"):
                    print(f"    Grading error: {grades['grading_error']}")
                else:
                    print(f"    Grades: R={grades.get('realness_score')}, O={grades.get('overall_score')}")
        
        results.append(result)
    
    return results

def calculate_summary(results):
    """Calculate summary statistics"""
    valid_results = [r for r in results if not r["error"]]
    
    if not valid_results:
        return {
            "trials": len(results),
            "latency_avg_s": 0,
            "latency_min_s": 0,
            "latency_max_s": 0,
            "tokens_per_sec_avg": 0,
            "completion_tokens_avg": 0,
            "last_sample_output_preview": ""
        }
    
    latencies = [r["latency_s"] for r in valid_results]
    tokens_per_sec = [r["tokens_per_sec"] for r in valid_results]
    completion_tokens = [r["completion_tokens"] for r in valid_results]
    
    return {
        "trials": len(results),
        "latency_avg_s": sum(latencies) / len(latencies),
        "latency_min_s": min(latencies),
        "latency_max_s": max(latencies),
        "tokens_per_sec_avg": sum(tokens_per_sec) / len(tokens_per_sec),
        "completion_tokens_avg": sum(completion_tokens) / len(completion_tokens),
        "last_sample_output_preview": valid_results[-1]["sample_output"][:200] if valid_results else ""
    }

def main():
    parser = argparse.ArgumentParser(description="Model benchmarking tool")
    parser.add_argument("--config", default="config/config.json", help="Config file path")
    parser.add_argument("--out_csv", help="Summary CSV output path")
    parser.add_argument("--out_trials_csv", help="Trials CSV output path")
    parser.add_argument("--dry-run", action="store_true", help="Test mode with mocked responses")
    
    args = parser.parse_args()
    
    # Load config
    config = load_config(args.config)
    
    # No validation needed - we'll use whatever models are available
    
    if not config["base_url"].startswith(("http://", "https://")):
        print("ERROR: Invalid base_url")
        return 1
    
    # Generate output filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_csv = args.out_csv or f"bakeoff_{timestamp}.csv"
    trials_csv = args.out_trials_csv or f"bakeoff_trials_{timestamp}.csv"
    gan_csv = f"bakeoff_gan_{timestamp}.csv"
    
    # Detect system info
    system_info = detect_system_info()
    
    print(f"Model Bakeoff")
    print(f"Machine: {config['machine_name']}")
    print(f"GPU: {system_info['gpu_info']} ({system_info['gpu_memory']})")
    print(f"Platform: {system_info['platform']}")
    print(f"Base URL: {config['base_url']}")
    print(f"Trials per model: {config['trials']}")
    print(f"Unload between models: {config['unload_between_models']}")
    print()
    
    # Dry run mode
    if args.dry_run:
        print("DRY RUN MODE - Using mock responses")
        candidate_models = ["mock-model-1", "mock-model-2"]
    else:
        # Fetch available models
        available_models = fetch_available_models(
            config["base_url"], 
            config["api_key"], 
            config["timeout_s"]
        )
        
        if not available_models:
            print("ERROR: Could not fetch available models")
            return 1
        
        candidate_models = get_candidate_models(available_models)
        
        if not candidate_models:
            print("ERROR: No models are available")
            return 1
    
    print(f"Testing models: {candidate_models}")
    print()
    
    # Open CSV files
    with open(trials_csv, 'w', newline='', encoding='utf-8') as trials_file, \
         open(summary_csv, 'w', newline='', encoding='utf-8') as summary_file, \
         open(gan_csv, 'w', newline='', encoding='utf-8') as gan_file:
        
        # CSV writers
        trial_writer = csv.writer(trials_file)
        summary_writer = csv.writer(summary_file)
        gan_writer = csv.writer(gan_file)
        
        # Write headers
        trial_writer.writerow([
            "trial_id", "timestamp", "machine_name", "gpu_info", "gpu_memory", "platform",
            "model", "trial", "latency_s", "completion_tokens", "tokens_per_sec", "sample_output"
        ])
        
        gan_writer.writerow([
            "trial_id", "timestamp", "model", "trial", "realness_score", "coherence_score",
            "naturalness_score", "overall_score", "brief_feedback", "grading_error"
        ])
        
        summary_writer.writerow([
            "timestamp", "machine_name", "gpu_info", "gpu_memory", "platform",
            "model", "trials", "latency_avg_s", "latency_min_s", "latency_max_s", 
            "tokens_per_sec_avg", "completion_tokens_avg", "unload_code", 
            "unload_stdout", "unload_stderr", "last_sample_output_preview"
        ])
        
        # Run trials for each model
        for i, model in enumerate(candidate_models, 1):
            print(f"Running model: {model} ({i} of {len(candidate_models)})")
            
            if args.dry_run:
                # Mock results
                results = [
                    {"error": None, "latency_s": 2.5, "completion_tokens": 150, 
                     "tokens_per_sec": 60, "sample_output": "Mock response"}
                    for _ in range(config["trials"])
                ]
                
                # Write mock trial rows
                for trial in range(1, config["trials"] + 1):
                    trial_id = f"{model}_{trial}_mock"
                    trial_writer.writerow([
                        trial_id, datetime.now().isoformat(), config["machine_name"], 
                        system_info["gpu_info"], system_info["gpu_memory"], system_info["platform"],
                        model, trial, 2.5, 150, 60, "Mock response"
                    ])
                    gan_writer.writerow([
                        trial_id, datetime.now().isoformat(), model, trial, 8, 9, 7, 8, "Mock grading", ""
                    ])
            else:
                results = run_trials_for_model(config, model, trial_writer, gan_writer, system_info)
            
            # Calculate summary
            summary = calculate_summary(results)
            
            # Unload models if requested
            unload_result = {"code": 0, "stdout": "", "stderr": ""}
            if config["unload_between_models"] and i < len(candidate_models):
                print("  Unloading models...")
                unload_result = unload_models()
                print(f"  Unload result: {unload_result['code']}")
                if unload_result["stderr"]:
                    print(f"  {unload_result['stderr']}")
            
            # Write summary row
            summary_writer.writerow([
                datetime.now().isoformat(),
                config["machine_name"],
                system_info["gpu_info"],
                system_info["gpu_memory"],
                system_info["platform"],
                model,
                summary["trials"],
                summary["latency_avg_s"],
                summary["latency_min_s"],
                summary["latency_max_s"],
                summary["tokens_per_sec_avg"],
                summary["completion_tokens_avg"],
                unload_result["code"],
                unload_result["stdout"],
                unload_result["stderr"],
                summary["last_sample_output_preview"]
            ])
            
            print(f"  Summary: {summary['latency_avg_s']:.2f}s avg, {summary['tokens_per_sec_avg']:.1f} tok/s avg")
            print()
    
    print(f"Results written to:")
    print(f"  Summary: {summary_csv}")
    print(f"  Trials: {trials_csv}")
    print(f"  GAN Grades: {gan_csv}")
    
    return 0

if __name__ == "__main__":
    exit(main())