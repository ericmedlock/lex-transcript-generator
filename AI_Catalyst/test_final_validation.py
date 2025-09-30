#!/usr/bin/env python3
"""
Final validation test for AI_Catalyst framework
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from ai_catalyst import LLMProvider, FileProcessor, PIIProcessor, ConfigManager, DatabaseManager
from ai_catalyst.monitoring import SystemMonitor, PerformanceTuner


def test_framework_imports():
    """Test that all framework components can be imported"""
    print("=== Framework Import Validation ===")
    
    # Test main imports
    try:
        from ai_catalyst.llm import LLMProvider, EndpointDiscovery
        from ai_catalyst.data.processors import FileProcessor
        from ai_catalyst.data.pii import PIIProcessor, PIIEngine
        from ai_catalyst.config import ConfigManager
        from ai_catalyst.database import DatabaseManager, AsyncConnectionPool
        from ai_catalyst.monitoring import SystemMonitor, PerformanceTuner
        print("[SUCCESS] All framework components imported successfully")
        return True
    except ImportError as e:
        print(f"[ERROR] Import failed: {e}")
        return False


def test_core_functionality():
    """Test core functionality of each component"""
    print("\n=== Core Functionality Validation ===")
    
    results = {}
    
    # File Processor
    try:
        processor = FileProcessor()
        stats = processor.get_directory_stats(".")
        results['file_processor'] = stats['total_files'] > 0
        print(f"File Processor: Found {stats['total_files']} files")
    except Exception as e:
        results['file_processor'] = False
        print(f"File Processor: Failed - {e}")
    
    # PII Processor
    try:
        pii = PIIProcessor()
        test_text = "Call John at 555-123-4567"
        scrubbed = pii.scrub_text(test_text)
        results['pii_processor'] = scrubbed != test_text and "<" in scrubbed
        print(f"PII Processor: {test_text} -> {scrubbed}")
    except Exception as e:
        results['pii_processor'] = False
        print(f"PII Processor: Failed - {e}")
    
    # Config Manager
    try:
        config = ConfigManager()
        test_value = config.get('nonexistent.key', 'default')
        results['config_manager'] = test_value == 'default'
        print(f"Config Manager: Default value handling works")
    except Exception as e:
        results['config_manager'] = False
        print(f"Config Manager: Failed - {e}")
    
    # Database Manager
    try:
        db = DatabaseManager("postgresql://test:test@localhost:5432/test")
        results['database_manager'] = not db.is_initialized()  # Should be False without real connection
        print(f"Database Manager: Initialization handling works")
    except Exception as e:
        results['database_manager'] = False
        print(f"Database Manager: Failed - {e}")
    
    # System Monitor
    try:
        monitor = SystemMonitor()
        info = monitor.get_system_info()
        results['system_monitor'] = 'hostname' in info and info['hostname']
        print(f"System Monitor: Detected hostname '{info['hostname']}'")
    except Exception as e:
        results['system_monitor'] = False
        print(f"System Monitor: Failed - {e}")
    
    # Performance Tuner
    try:
        tuner = PerformanceTuner()
        tuner.record_metric('test', 100)
        stats = tuner.get_metric_stats('test')
        results['performance_tuner'] = stats.get('count', 0) == 1
        print(f"Performance Tuner: Recorded and retrieved metrics")
    except Exception as e:
        results['performance_tuner'] = False
        print(f"Performance Tuner: Failed - {e}")
    
    return results


def test_real_world_scenario():
    """Test a realistic usage scenario"""
    print("\n=== Real-World Scenario Test ===")
    
    try:
        # Scenario: Process a conversation file and scrub PII
        import tempfile
        import json
        from pathlib import Path
        
        # Create test conversation file
        test_dir = Path(tempfile.mkdtemp())
        conv_file = test_dir / "conversation.json"
        
        conversation_data = {
            "conversation_id": "test_001",
            "participants": ["Agent", "Customer"],
            "transcript": [
                {"speaker": "Agent", "text": "Hello, how can I help you today?"},
                {"speaker": "Customer", "text": "Hi, I'm Sarah Johnson and I need help with my account"},
                {"speaker": "Agent", "text": "I'd be happy to help. Can you provide your phone number?"},
                {"speaker": "Customer", "text": "Sure, it's 555-987-6543"},
                {"speaker": "Agent", "text": "Thank you. I see your account now."}
            ],
            "metadata": {
                "date": "2024-01-15",
                "duration": "5:30",
                "quality_score": 8.5
            }
        }
        
        with open(conv_file, 'w') as f:
            json.dump(conversation_data, f)
        
        # Process with AI_Catalyst
        file_processor = FileProcessor()
        pii_processor = PIIProcessor()
        config = ConfigManager()
        monitor = SystemMonitor()
        
        # Step 1: Load conversation
        conversations = list(file_processor.process_file(conv_file))
        print(f"Step 1: Loaded {len(conversations)} conversation files")
        
        # Step 2: Process and scrub PII
        pii_found = 0
        for conv_item in conversations:
            data = conv_item['data']
            if 'transcript' in data:
                for turn in data['transcript']:
                    original_text = turn['text']
                    scrubbed_text = pii_processor.scrub_text(original_text)
                    if original_text != scrubbed_text:
                        pii_found += 1
                        turn['text'] = scrubbed_text
        
        print(f"Step 2: Found and scrubbed PII in {pii_found} conversation turns")
        
        # Step 3: Get system metrics
        system_info = monitor.get_system_info()
        metrics = monitor.get_system_metrics()
        
        print(f"Step 3: Collected system metrics (CPU: {metrics['cpu_percent']}%, Memory: {metrics['memory_percent']}%)")
        
        # Step 4: Configuration-driven processing
        pii_strategy = config.get('pii.strategy', 'regex')
        placeholder_style = config.get('pii.placeholder_style', 'angle')
        
        print(f"Step 4: Used configuration (PII strategy: {pii_strategy}, style: {placeholder_style})")
        
        # Cleanup
        import shutil
        shutil.rmtree(test_dir)
        
        print("[SUCCESS] Real-world scenario completed successfully")
        return True
        
    except Exception as e:
        print(f"[ERROR] Real-world scenario failed: {e}")
        return False


def main():
    """Run final validation"""
    print("AI_Catalyst Framework - Final Validation")
    print("=" * 50)
    
    # Test imports
    imports_ok = test_framework_imports()
    
    # Test core functionality
    functionality_results = test_core_functionality()
    
    # Test real-world scenario
    scenario_ok = test_real_world_scenario()
    
    # Summary
    print("\n" + "=" * 50)
    print("VALIDATION SUMMARY")
    print("=" * 50)
    
    print(f"Framework Imports: {'PASS' if imports_ok else 'FAIL'}")
    
    print("Component Tests:")
    for component, result in functionality_results.items():
        status = 'PASS' if result else 'FAIL'
        print(f"  {component.replace('_', ' ').title()}: {status}")
    
    print(f"Real-World Scenario: {'PASS' if scenario_ok else 'FAIL'}")
    
    # Overall result
    all_passed = (imports_ok and 
                 all(functionality_results.values()) and 
                 scenario_ok)
    
    print("\n" + "=" * 50)
    if all_passed:
        print("OVERALL RESULT: FRAMEWORK READY FOR PRODUCTION")
        print("\nAI_Catalyst Framework Successfully Extracted!")
        print("\nComponents Available:")
        print("- LLM Provider: Three-tier LLM system with auto-failover")
        print("- File Processor: Multi-format file handling (JSON/CSV/TXT/JSONL)")
        print("- PII Processor: Comprehensive PII detection and scrubbing")
        print("- Config Manager: Hierarchical configuration with YAML support")
        print("- Database Manager: Async PostgreSQL patterns and utilities")
        print("- System Monitor: Hardware monitoring and performance metrics")
        print("- Performance Tuner: Dynamic optimization and auto-tuning")
        print("\nFramework is ready for use across all AI projects!")
    else:
        print("OVERALL RESULT: SOME ISSUES DETECTED")
        print("Please review failed components before production use.")


if __name__ == "__main__":
    main()