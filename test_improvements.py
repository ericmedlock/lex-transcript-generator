#!/usr/bin/env python3
"""
Test script for Phase 1 improvements
"""

import asyncio
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src', 'nodes'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'src', 'core'))

async def test_model_manager():
    """Test enhanced model discovery"""
    print("=== Testing Model Manager ===")
    
    try:
        from generation_node import ModelManager
        
        model_manager = ModelManager("http://localhost:1234/v1/chat/completions")
        
        # Test model discovery
        models = await model_manager.discover_models()
        print(f"Discovered models: {models}")
        
        # Test best model selection
        best_model = await model_manager.get_best_model()
        print(f"Best model: {best_model}")
        
        # Test model validation
        if models:
            is_valid = await model_manager.validate_model(models[0])
            print(f"Model {models[0]} validation: {is_valid}")
        
    except Exception as e:
        print(f"Model Manager test failed: {e}")

def test_prompt_manager():
    """Test prompt randomization"""
    print("\n=== Testing Prompt Manager ===")
    
    try:
        from generation_node import PromptManager
        
        prompt_manager = PromptManager()
        
        # Test healthcare prompt generation
        for i in range(3):
            prompt = prompt_manager.generate_varied_prompt(
                "Schedule a medical appointment", 
                "Healthcare Appointment Scheduling"
            )
            print(f"\nPrompt {i+1}:")
            print(prompt[:200] + "..." if len(prompt) > 200 else prompt)
        
    except Exception as e:
        print(f"Prompt Manager test failed: {e}")

def test_dedupe_manager():
    """Test enhanced deduplication"""
    print("\n=== Testing Deduplication Manager ===")
    
    try:
        from dedupe_manager import DedupeManager
        
        dedupe_manager = DedupeManager()
        
        # Test model-specific strategies
        models_to_test = ["google/gemma-3-1b", "microsoft/phi-4", "meta/llama-3", "openai/gpt-4"]
        
        for model in models_to_test:
            strategy = dedupe_manager.get_dedup_strategy(model)
            print(f"{model}: hash_only={strategy['hash_only']}, threshold={strategy['threshold']}")
        
    except Exception as e:
        print(f"Deduplication Manager test failed: {e}")

def test_config_manager():
    """Test configuration management"""
    print("\n=== Testing Config Manager ===")
    
    try:
        sys.path.append(os.path.join(os.path.dirname(__file__), 'src', 'master'))
        from orchestrator import ConfigManager
        
        config_manager = ConfigManager("config/config.json")
        
        # Test configuration loading
        machine_name = config_manager.get("machine_name")
        trials = config_manager.get("trials")
        conversations_per_trial = config_manager.get("conversations_per_trial")
        
        print(f"Machine: {machine_name}")
        print(f"Target conversations: {trials} × {conversations_per_trial} = {trials * conversations_per_trial}")
        
        # Test output directory creation
        output_dir = config_manager.setup_output_directory("test", "12345")
        print(f"Output directory: {output_dir}")
        
        # Test filename generation
        filename = config_manager.generate_filename("test_results")
        print(f"Generated filename: {filename}")
        
    except Exception as e:
        print(f"Config Manager test failed: {e}")

async def main():
    """Run all tests"""
    print("Testing Phase 1 Improvements")
    print("=" * 50)
    
    await test_model_manager()
    test_prompt_manager()
    test_dedupe_manager()
    test_config_manager()
    
    print("\n" + "=" * 50)
    print("Phase 1 testing complete!")

if __name__ == "__main__":
    asyncio.run(main())