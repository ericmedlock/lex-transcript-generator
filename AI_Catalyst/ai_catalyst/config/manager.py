"""
Config Manager - Database-first configuration with YAML fallbacks

Supports hierarchical configuration management with database priority and YAML fallbacks.
"""

import os
import yaml
import asyncio
from typing import Any, Dict, Optional, Union, List
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class ConfigValue:
    """Configuration value with metadata"""
    key: str
    value: Any
    data_type: str
    description: str = ""
    category: str = ""
    is_sensitive: bool = False


class ConfigManager:
    """Database-first configuration manager with YAML fallbacks"""
    
    def __init__(self, config_file: Optional[Union[str, Path]] = None, db_config: Optional[Dict] = None):
        """
        Initialize configuration manager
        
        Args:
            config_file: Path to YAML config file (default: config/default_config.yaml)
            db_config: Database configuration dict with keys: host, port, database, user, password
        """
        self.config_file = Path(config_file) if config_file else Path("config/default_config.yaml")
        self.db_config = db_config
        self.db_available = False
        self._config_cache = {}
        self._yaml_config = {}
        self._load_yaml_config()
        
        # Try to initialize database connection
        if self.db_config:
            self._check_db_availability()
    
    def _load_yaml_config(self):
        """Load YAML configuration as fallback"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    self._yaml_config = yaml.safe_load(f) or {}
                logger.info(f"Loaded YAML config from {self.config_file}")
            except Exception as e:
                logger.error(f"Failed to load YAML config: {e}")
                self._yaml_config = {}
        else:
            logger.warning(f"YAML config file not found: {self.config_file}")
            self._yaml_config = {}
    
    def _check_db_availability(self):
        """Check if database is available (sync version for init)"""
        try:
            # Try to import database dependencies
            import psycopg2
            
            # Test connection
            conn = psycopg2.connect(**self.db_config)
            conn.close()
            self.db_available = True
            logger.info("Database connection available")
        except Exception as e:
            logger.warning(f"Database not available, using YAML only: {e}")
            self.db_available = False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value with database priority, YAML fallback
        
        Args:
            key: Configuration key (supports dot notation)
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        # Check cache first
        if key in self._config_cache:
            return self._config_cache[key]
        
        # Try database first (if available)
        if self.db_available:
            try:
                value = self._get_from_database(key)
                if value is not None:
                    self._config_cache[key] = value
                    return value
            except Exception as e:
                logger.warning(f"Database config lookup failed for {key}: {e}")
        
        # Fall back to YAML
        value = self._get_nested_value(self._yaml_config, key, default)
        self._config_cache[key] = value
        return value
    
    def set(self, key: str, value: Any, description: str = "", category: str = ""):
        """
        Set configuration value (YAML only in this sync version)
        
        Args:
            key: Configuration key
            value: Configuration value
            description: Description of the configuration
            category: Category for grouping
        """
        # For now, just update cache and YAML
        self._config_cache[key] = value
        
        # Update YAML structure
        self._set_nested_value(self._yaml_config, key, value)
        
        # Save to file
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w') as f:
                yaml.dump(self._yaml_config, f, default_flow_style=False)
            logger.info(f"Updated config key {key} in YAML")
        except Exception as e:
            logger.error(f"Failed to save YAML config: {e}")
    
    def get_category(self, category: str) -> Dict[str, Any]:
        """
        Get all configuration values for a category
        
        Args:
            category: Category name
            
        Returns:
            Dictionary of configuration values
        """
        if self.db_available:
            try:
                return self._get_category_from_database(category)
            except Exception as e:
                logger.warning(f"Database category lookup failed for {category}: {e}")
        
        # Fall back to YAML
        return self._yaml_config.get(category, {})
    
    def get_all_keys(self) -> List[str]:
        """
        Get all available configuration keys
        
        Returns:
            List of configuration keys
        """
        keys = set()
        
        # Add YAML keys
        keys.update(self._flatten_dict_keys(self._yaml_config))
        
        # Add database keys if available
        if self.db_available:
            try:
                db_keys = self._get_all_db_keys()
                keys.update(db_keys)
            except Exception as e:
                logger.warning(f"Failed to get database keys: {e}")
        
        return sorted(list(keys))
    
    def _get_nested_value(self, config: dict, key: str, default: Any) -> Any:
        """Get nested value from dict using dot notation"""
        keys = key.split('.')
        value = config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def _set_nested_value(self, config: dict, key: str, value: Any):
        """Set nested value in dict using dot notation"""
        keys = key.split('.')
        current = config
        
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        current[keys[-1]] = value
    
    def _flatten_dict_keys(self, d: dict, prefix: str = "") -> List[str]:
        """Flatten dictionary keys with dot notation"""
        keys = []
        for k, v in d.items():
            full_key = f"{prefix}.{k}" if prefix else k
            keys.append(full_key)
            if isinstance(v, dict):
                keys.extend(self._flatten_dict_keys(v, full_key))
        return keys
    
    def _get_from_database(self, key: str) -> Any:
        """Get value from database (placeholder for async version)"""
        # This would be implemented with actual database calls
        # For now, return None to fall back to YAML
        return None
    
    def _get_category_from_database(self, category: str) -> Dict[str, Any]:
        """Get category from database (placeholder for async version)"""
        # This would be implemented with actual database calls
        return {}
    
    def _get_all_db_keys(self) -> List[str]:
        """Get all keys from database (placeholder for async version)"""
        # This would be implemented with actual database calls
        return []
    
    def reload_cache(self):
        """Reload configuration cache"""
        self._config_cache.clear()
        self._load_yaml_config()
        logger.info("Configuration cache reloaded")
    
    def has_database(self) -> bool:
        """Check if database is available"""
        return self.db_available
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get summary of configuration sources and status"""
        return {
            'yaml_file': str(self.config_file),
            'yaml_exists': self.config_file.exists(),
            'database_available': self.db_available,
            'cached_keys': len(self._config_cache),
            'yaml_keys': len(self._flatten_dict_keys(self._yaml_config))
        }