#!/usr/bin/env python3
"""
Debug Test - Single conversation workflow test
"""

import yaml
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.discovery.model_discovery import ModelDiscovery
from src.testing.prompt_executor import PromptExecutor
from src.monitoring.resource_monitor import ResourceMonitor
from src.scoring.quality_scorer import QualityScorer

def debug_test():
    print("=== Debug Test - Single Conversation Workflow ===")
    
    # Initialize components
    discovery = ModelDiscovery()
    executor = PromptExecutor()
    monitor = ResourceMonitor()
    scorer = QualityScorer()
    
    # Load prompts
    with open("config/test_prompts.yaml", "r") as f:
        prompts_config = yaml.safe_load(f)
    
    # Get first available model
    print("1. Discovering models...")
    models = discovery.discover_conversational_models()
    if not models:
        print("ERROR: No models found")
        return
    
    model = models[0]
    print(f"   Using model: {model['id']}")
    
    # Test model availability
    print("2. Testing model availability...")
    if not discovery.test_model_availability(model['id']):
        print("ERROR: Model not responsive")
        return
    print("   Model is responsive")
    
    # Get first prompt
    prompt_config = prompts_config["healthcare_appointment_prompts"][0]
    prompt_text = prompt_config["prompt"]
    print(f"3. Using prompt: {prompt_config['id']}")
    
    # Start monitoring
    print("4. Starting resource monitoring...")
    monitor.start_monitoring()
    
    # Execute prompt
    print("5. Executing prompt...")
    conversation, metrics = executor.execute_prompt(model['id'], prompt_text)
    
    # Stop monitoring
    resource_metrics = monitor.stop_monitoring()
    
    # Print results
    print("6. Execution Results:")
    print(f"   Success: {metrics['success']}")
    print(f"   Total time: {metrics['total_time']:.2f}s")
    print(f"   Tokens/sec: {metrics['tokens_per_second']:.2f}")
    print(f"   Total tokens: {metrics['total_tokens']}")
    print(f"   CPU avg: {resource_metrics['cpu_usage_avg']:.1f}%")
    print(f"   GPU avg: {resource_metrics['gpu_usage_avg']:.1f}%")
    
    if not metrics['success']:
        print(f"   ERROR: {metrics['error']}")
        return
    
    print("7. Generated Conversation (first 500 chars):")
    print(f"   {conversation[:500]}...")
    
    # Grade conversation
    print("8. Grading conversation...")
    scores = scorer.score_conversation(conversation, prompt_text)
    
    print("9. Quality Scores:")
    if scores.get('grading_error'):
        print(f"   ERROR: {scores['grading_error']}")
    else:
        print(f"   Realness: {scores.get('realness_score')}")
        print(f"   Coherence: {scores.get('coherence_score')}")
        print(f"   Naturalness: {scores.get('naturalness_score')}")
        print(f"   Overall: {scores.get('overall_score')}")
        print(f"   Healthcare Valid: {scores.get('healthcare_valid')}")
        print(f"   Feedback: {scores.get('brief_feedback')}")
    
    print("=== Debug Test Complete ===")

if __name__ == "__main__":
    debug_test()