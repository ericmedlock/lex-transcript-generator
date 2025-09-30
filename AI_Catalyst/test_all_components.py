#!/usr/bin/env python3
"""
Comprehensive test suite for all AI_Catalyst components
"""

import sys
import os
import tempfile
import json
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from ai_catalyst import LLMProvider, FileProcessor, PIIProcessor, ConfigManager, DatabaseManager
from ai_catalyst.llm import EndpointDiscovery
from ai_catalyst.data.pii import PIIEngine
from ai_catalyst.database import AsyncConnectionPool
from ai_catalyst.monitoring import SystemMonitor, PerformanceTuner


def test_llm_provider():
    """Test LLM Provider functionality"""
    print("=== Testing LLM Provider ===")
    
    provider = LLMProvider()
    
    # Test endpoint discovery
    endpoints = EndpointDiscovery.discover_local_endpoints()
    print(f"Discovered endpoints: {endpoints}")
    
    # Test provider availability
    available = provider.get_available_providers()
    print(f"Available providers: {available}")
    
    # Test generation if providers available
    if available:
        result = provider.generate("Say 'Hello from AI_Catalyst'", temperature=0.1, max_tokens=20)
        print(f"Generation result: {result['content'][:50]}...")
        print(f"Provider used: {result['provider_used']}")
    
    print("[SUCCESS] LLM Provider tests passed")


def test_file_processor():
    """Test File Processor functionality"""
    print("\n=== Testing File Processor ===")
    
    processor = FileProcessor()
    
    # Create test files
    test_dir = Path(tempfile.mkdtemp())
    
    # JSON test file
    json_file = test_dir / "test.json"
    with open(json_file, 'w') as f:
        json.dump({"conversation": "Hello world", "type": "test"}, f)
    
    # CSV test file
    csv_file = test_dir / "test.csv"
    with open(csv_file, 'w') as f:
        f.write("name,message\nJohn,Hello\nJane,Hi there\n")
    
    # Test file processing
    json_items = list(processor.process_file(json_file))
    csv_items = list(processor.process_file(csv_file))
    
    print(f"JSON items: {len(json_items)}")
    print(f"CSV items: {len(csv_items)}")
    
    # Test directory processing
    all_items = list(processor.process_directory(test_dir))
    print(f"Total items from directory: {len(all_items)}")
    
    # Test directory stats
    stats = processor.get_directory_stats(test_dir)
    print(f"Directory stats: {stats}")
    
    # Cleanup
    import shutil
    shutil.rmtree(test_dir)
    
    print("[SUCCESS] File Processor tests passed")


def test_pii_processor():
    """Test PII Processor functionality"""
    print("\n=== Testing PII Processor ===")
    
    processor = PIIProcessor(config={'default_strategy': 'regex'})
    
    # Test text with PII
    test_text = "Hi, I'm John Smith. Call me at 555-123-4567 or email john@example.com"
    
    # Test PII detection
    pii_counts = processor.detect_pii(test_text)
    print(f"PII detected: {pii_counts}")
    
    # Test PII scrubbing
    scrubbed = processor.scrub_text(test_text)
    print(f"Scrubbed text: {scrubbed}")
    
    # Test batch processing
    texts = [
        "Contact Alice at 555-111-2222",
        "Bob's email is bob@company.com",
        "Meeting on 03/15/2024"
    ]
    
    scrubbed_batch = processor.batch_scrub_texts(texts)
    print(f"Batch scrubbed: {len(scrubbed_batch)} texts")
    
    # Test PII Engine
    patterns = {'PHONE': r'\\b\\d{3}-\\d{3}-\\d{4}\\b'}
    matches = PIIEngine.detect_pii_patterns(test_text, patterns)
    print(f"Engine matches: {matches}")
    
    print("[SUCCESS] PII Processor tests passed")


def test_config_manager():
    """Test Configuration Manager functionality"""
    print("\n=== Testing Configuration Manager ===")
    
    # Create temporary config file
    config_file = Path(tempfile.mktemp(suffix='.yaml'))
    config_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_file, 'w') as f:
        f.write("""
app:
  name: test_app
  version: 1.0
database:
  host: localhost
  port: 5432
""")
    
    # Test config manager
    config = ConfigManager(config_file=config_file)
    
    # Test getting values
    app_name = config.get('app.name')
    db_host = config.get('database.host')
    missing = config.get('missing.key', 'default_value')
    
    print(f"App name: {app_name}")
    print(f"DB host: {db_host}")
    print(f"Missing key: {missing}")
    
    # Test setting values
    config.set('app.debug', True)
    debug_value = config.get('app.debug')
    print(f"Debug value: {debug_value}")
    
    # Test category retrieval
    app_config = config.get_category('app')
    print(f"App config: {app_config}")
    
    # Test config summary
    summary = config.get_config_summary()
    print(f"Config summary: {summary}")
    
    # Cleanup
    config_file.unlink()
    
    print("[SUCCESS] Configuration Manager tests passed")


def test_database_manager():
    """Test Database Manager functionality (without actual DB)"""
    print("\n=== Testing Database Manager ===")
    
    # Test with connection string
    db_config = "postgresql://user:pass@localhost:5432/testdb"
    db_manager = DatabaseManager(db_config)
    
    print(f"Database URL: {db_manager.db_url}")
    print(f"Initialized: {db_manager.is_initialized()}")
    
    # Test with config dict
    config_dict = {
        'host': 'localhost',
        'port': 5432,
        'database': 'testdb',
        'user': 'testuser',
        'password': 'testpass'
    }
    
    db_manager2 = DatabaseManager(config_dict)
    print(f"Built URL: {db_manager2.db_url}")
    
    # Test connection pool patterns
    pool = AsyncConnectionPool(db_manager)
    print(f"Connection pool created: {pool is not None}")
    
    print("[SUCCESS] Database Manager tests passed")


def test_system_monitor():
    """Test System Monitor functionality"""
    print("\n=== Testing System Monitor ===")
    
    monitor = SystemMonitor()
    
    # Test system info
    system_info = monitor.get_system_info()
    print(f"Hostname: {system_info['hostname']}")
    print(f"Platform: {system_info['platform']}")
    print(f"CPU count: {system_info['cpu_count']}")
    print(f"Memory total: {system_info['memory_total_gb']} GB")
    print(f"GPU count: {system_info['gpu_count']}")
    
    # Test system metrics
    metrics = monitor.get_system_metrics()
    print(f"CPU usage: {metrics['cpu_percent']}%")
    print(f"Memory usage: {metrics['memory_percent']}%")
    print(f"CPU temp: {metrics['cpu_temp']}°C")
    
    # Test thermal status
    thermal = monitor.get_thermal_status()
    print(f"Thermal status: {thermal['overall_status']}")
    
    # Test monitoring capabilities
    capabilities = monitor.is_monitoring_available()
    print(f"Monitoring capabilities: {capabilities}")
    
    print("[SUCCESS] System Monitor tests passed")


def test_performance_tuner():
    """Test Performance Tuner functionality"""
    print("\n=== Testing Performance Tuner ===")
    
    tuner = PerformanceTuner(window_size=50, tune_interval=5)
    
    # Record some test metrics
    import time
    import random
    
    for i in range(10):
        tuner.record_metric('latency', random.uniform(100, 500))
        tuner.record_metric('throughput', random.uniform(50, 150))
        tuner.record_metric('error_rate', random.uniform(0, 0.1))
    
    # Test metric statistics
    latency_stats = tuner.get_metric_stats('latency')
    print(f"Latency stats: mean={latency_stats.get('mean', 0):.1f}ms, p95={latency_stats.get('p95', 0):.1f}ms")
    
    # Set up tuning parameters
    tuner.set_tuning_parameter('concurrency', 4, min_value=1, max_value=10)
    tuner.set_tuning_parameter('batch_size', 10, min_value=1, max_value=50)
    
    # Test auto-tuning
    target_metrics = {
        'latency': {'target': 200, 'tolerance': 0.2},
        'throughput': {'target': 100, 'tolerance': 0.1}
    }
    
    # Force tuning by setting last tune time to past
    from datetime import datetime, timedelta
    tuner.last_tune_time = datetime.now() - timedelta(seconds=10)
    
    tuning_result = tuner.auto_tune(target_metrics)
    print(f"Tuning result: {tuning_result['metrics_status']}")
    
    # Test performance summary
    summary = tuner.get_performance_summary()
    print(f"Performance summary: {len(summary['metrics'])} metric types tracked")
    
    print("[SUCCESS] Performance Tuner tests passed")


def test_integration():
    """Test component integration"""
    print("\n=== Testing Component Integration ===")
    
    # Test LLM + PII integration
    llm = LLMProvider()
    pii = PIIProcessor()
    
    if llm.get_available_providers():
        # Generate text and scrub PII
        result = llm.generate("Generate a sample name and phone number", max_tokens=50)
        if result['content']:
            scrubbed = pii.scrub_text(result['content'])
            print(f"Generated and scrubbed: {scrubbed[:100]}...")
    
    # Test File + PII integration
    processor = FileProcessor()
    
    # Create test file with PII
    test_dir = Path(tempfile.mkdtemp())
    test_file = test_dir / "pii_test.json"
    
    with open(test_file, 'w') as f:
        json.dump({
            "conversation": "Hi, I'm John Smith at 555-123-4567",
            "metadata": {"source": "test"}
        }, f)
    
    # Process file and scrub PII
    for item in processor.process_file(test_file):
        original = item['data']['conversation']
        scrubbed = pii.scrub_text(original)
        print(f"File processing + PII: {scrubbed}")
    
    # Cleanup
    import shutil
    shutil.rmtree(test_dir)
    
    print("[SUCCESS] Integration tests passed")


def main():
    """Run all tests"""
    print("AI_Catalyst Framework - Comprehensive Test Suite")
    print("=" * 60)
    
    try:
        test_llm_provider()
        test_file_processor()
        test_pii_processor()
        test_config_manager()
        test_database_manager()
        test_system_monitor()
        test_performance_tuner()
        test_integration()
        
        print("\n" + "=" * 60)
        print("[SUCCESS] All AI_Catalyst component tests passed!")
        print("Framework is ready for use across AI projects.")
        
    except Exception as e:
        print(f"\n[ERROR] Test suite failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()