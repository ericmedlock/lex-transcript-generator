"""Configuration management module"""

import yaml
from pathlib import Path
from typing import Any, Optional, Dict

class ConfigManager:
    """Manage configuration loading and access"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        search_paths = []
        
        if self.config_path:
            search_paths.append(self.config_path)
        
        # Default search paths
        search_paths.extend([
            'config/default_config.yaml',
            '../config/default_config.yaml',
            Path(__file__).parent.parent.parent / 'config' / 'default_config.yaml'
        ])
        
        for path in search_paths:
            path_obj = Path(path)
            if path_obj.exists():
                try:
                    with open(path_obj, 'r') as f:
                        config = yaml.safe_load(f)
                    print(f"Loaded config from: {path_obj}")
                    return config
                except Exception as e:
                    print(f"Error loading config from {path_obj}: {e}")
                    continue
        
        print("No config file found, using defaults")
        return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            'processing': {
                'batch_size': 100,
                'parallel_workers': 4,
                'cache_enabled': True
            },
            'llm': {
                'default_provider': 'openai',
                'classification_model': 'gpt-4o-mini'
            },
            'output': {
                'template_format': 'yaml',
                'include_examples': True
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation"""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value using dot notation"""
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value