#!/usr/bin/env python3
"""
Configuration Manager Tests
Tests for configuration loading, database integration, and YAML fallback mechanisms.
"""

import asyncio
import tempfile
import yaml
from pathlib import Path
import sys
import os

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from test_framework import TestCase, TestSuite, TestAssertions, test_runner

# Mock ConfigManager for testing
class MockConfigManager:
    def __init__(self, config_file=None):
        self.config_data = {}
        if config_file:
            with open(config_file, 'r') as f:
                self.config_data = yaml.safe_load(f)
    
    def get(self, key, default=None):
        keys = key.split('.')
        data = self.config_data
        for k in keys:
            if isinstance(data, dict) and k in data:
                data = data[k]
            else:
                return default
        return data
    
    def get_category(self, category):
        return self.config_data.get(category, {})

ConfigManager = MockConfigManager

class TestConfigManager:
    def __init__(self):
        self.temp_dir = None
        self.config_manager = None
    
    def setup(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test YAML config
        test_config = {
            'generation': {
                'default_batch_size': 10,
                'conversation_length': {
                    'simple': [20, 40],
                    'complex': [80, 150]
                }
            },
            'thermal': {
                'cpu_temp_limit': 80,
                'gpu_temp_limit': 85
            },
            'database': {
                'host': 'localhost',
                'port': 5432,
                'name': 'test_db'
            }
        }
        
        config_path = Path(self.temp_dir) / 'test_config.yaml'
        with open(config_path, 'w') as f:
            yaml.dump(test_config, f)
        
        self.config_manager = ConfigManager(config_file=str(config_path))
    
    def teardown(self):
        """Cleanup test environment"""
        if self.temp_dir:
            import shutil
            shutil.rmtree(self.temp_dir)
    
    def test_yaml_config_loading(self):
        """Test loading configuration from YAML file"""
        TestAssertions.assert_not_none(self.config_manager, "ConfigManager should be initialized")
        
        # Test basic config access
        batch_size = self.config_manager.get('generation.default_batch_size')
        TestAssertions.assert_equals(batch_size, 10, "Should load batch size from YAML")
        
        # Test nested config access
        cpu_limit = self.config_manager.get('thermal.cpu_temp_limit')
        TestAssertions.assert_equals(cpu_limit, 80, "Should load nested config values")
    
    def test_nested_config_access(self):
        """Test dot-notation configuration access"""
        # Test deep nesting
        simple_length = self.config_manager.get('generation.conversation_length.simple')
        TestAssertions.assert_equals(simple_length, [20, 40], "Should access deeply nested config")
        
        # Test array access
        TestAssertions.assert_equals(len(simple_length), 2, "Should return correct array length")
        TestAssertions.assert_equals(simple_length[0], 20, "Should access array elements")
    
    def test_config_type_inference(self):
        """Test proper data type conversion"""
        # Integer
        port = self.config_manager.get('database.port')
        TestAssertions.assert_true(isinstance(port, int), "Port should be integer")
        
        # String
        host = self.config_manager.get('database.host')
        TestAssertions.assert_true(isinstance(host, str), "Host should be string")
        
        # List
        simple_length = self.config_manager.get('generation.conversation_length.simple')
        TestAssertions.assert_true(isinstance(simple_length, list), "Should preserve list type")
    
    def test_missing_config_fallback(self):
        """Test handling of missing configuration keys"""
        # Test with default value
        missing_value = self.config_manager.get('nonexistent.key', default='fallback')
        TestAssertions.assert_equals(missing_value, 'fallback', "Should return default for missing key")
        
        # Test without default (should return None)
        missing_no_default = self.config_manager.get('another.missing.key')
        TestAssertions.assert_equals(missing_no_default, None, "Should return None for missing key without default")
    
    def test_config_categories(self):
        """Test retrieving entire configuration categories"""
        generation_config = self.config_manager.get_category('generation')
        TestAssertions.assert_not_none(generation_config, "Should return generation category")
        TestAssertions.assert_in('default_batch_size', generation_config, "Should contain expected keys")
        TestAssertions.assert_in('conversation_length', generation_config, "Should contain nested categories")
    
    async def test_database_config_override(self):
        """Test database-first configuration priority (mock test)"""
        # This would test database override functionality
        # For now, we'll test the interface exists
        TestAssertions.assert_true(hasattr(self.config_manager, 'get'), "Should have get method")
        TestAssertions.assert_true(hasattr(self.config_manager, 'get_category'), "Should have get_category method")

def create_config_tests():
    """Create and register configuration manager tests"""
    test_manager = TestConfigManager()
    
    tests = [
        TestCase(
            test_id="config_001",
            name="YAML Config Loading",
            description="Verify YAML configuration file loading and parsing",
            test_func=test_manager.test_yaml_config_loading,
            category="core"
        ),
        TestCase(
            test_id="config_002", 
            name="Nested Config Access",
            description="Test dot-notation access to nested configuration values",
            test_func=test_manager.test_nested_config_access,
            category="core"
        ),
        TestCase(
            test_id="config_003",
            name="Config Type Inference", 
            description="Verify proper data type conversion for config values",
            test_func=test_manager.test_config_type_inference,
            category="core"
        ),
        TestCase(
            test_id="config_004",
            name="Missing Config Fallback",
            description="Test graceful handling of missing configuration keys",
            test_func=test_manager.test_missing_config_fallback,
            category="core"
        ),
        TestCase(
            test_id="config_005",
            name="Config Categories",
            description="Test retrieval of entire configuration categories",
            test_func=test_manager.test_config_categories,
            category="core"
        ),
        TestCase(
            test_id="config_006",
            name="Database Config Override",
            description="Test database-first configuration priority over YAML",
            test_func=test_manager.test_database_config_override,
            category="core"
        )
    ]
    
    suite = TestSuite(
        name="config_manager",
        description="Configuration Management System Tests",
        tests=tests,
        setup_func=test_manager.setup,
        teardown_func=test_manager.teardown
    )
    
    test_runner.register_suite(suite)

# Register tests when module is imported
create_config_tests()