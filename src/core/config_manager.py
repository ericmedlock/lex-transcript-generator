"""Configuration Manager - Database-first configuration with YAML fallbacks"""

import os
import yaml
import asyncio
from typing import Any, Dict, Optional, Union
from pathlib import Path
import asyncpg
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ConfigValue:
    key: str
    value: Any
    data_type: str
    description: str = ""
    category: str = ""
    is_sensitive: bool = False


class ConfigManager:
    def __init__(self, config_file: str = "config/default_config.yaml", db_url: str = None):
        self.config_file = Path(config_file)
        self.db_url = db_url
        self.db_pool = None
        self._config_cache = {}
        self._yaml_config = {}
        self._load_yaml_config()

    def _load_yaml_config(self):
        """Load YAML configuration as fallback"""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                self._yaml_config = yaml.safe_load(f)

    async def initialize_db(self):
        """Initialize database connection pool"""
        if self.db_url:
            self.db_pool = await asyncpg.create_pool(self.db_url)

    async def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value with database priority, YAML fallback"""
        # Check cache first
        if key in self._config_cache:
            return self._config_cache[key]

        # Try database first
        if self.db_pool:
            try:
                async with self.db_pool.acquire() as conn:
                    row = await conn.fetchrow(
                        "SELECT value, data_type FROM system_config WHERE key = $1", key
                    )
                    if row:
                        value = self._convert_value(row['value'], row['data_type'])
                        self._config_cache[key] = value
                        return value
            except Exception:
                pass  # Fall back to YAML

        # Fall back to YAML
        value = self._get_nested_value(self._yaml_config, key, default)
        self._config_cache[key] = value
        return value

    async def set(self, key: str, value: Any, description: str = "", category: str = ""):
        """Set configuration value in database"""
        if not self.db_pool:
            raise RuntimeError("Database not initialized")

        data_type = self._infer_data_type(value)
        value_str = str(value)

        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO system_config (key, value, data_type, description, category, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (key) DO UPDATE SET
                    value = EXCLUDED.value,
                    data_type = EXCLUDED.data_type,
                    description = EXCLUDED.description,
                    category = EXCLUDED.category,
                    updated_at = EXCLUDED.updated_at
            """, key, value_str, data_type, description, category, datetime.utcnow())

        # Update cache
        self._config_cache[key] = value

    async def get_category(self, category: str) -> Dict[str, Any]:
        """Get all configuration values for a category"""
        if not self.db_pool:
            return self._get_yaml_category(category)

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT key, value, data_type FROM system_config WHERE category = $1", 
                category
            )
            
            result = {}
            for row in rows:
                key = row['key'].split('.', 1)[1] if '.' in row['key'] else row['key']
                result[key] = self._convert_value(row['value'], row['data_type'])
            
            return result

    def _get_nested_value(self, config: dict, key: str, default: Any) -> Any:
        """Get nested value from YAML using dot notation"""
        keys = key.split('.')
        value = config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value

    def _get_yaml_category(self, category: str) -> Dict[str, Any]:
        """Get category from YAML config"""
        return self._yaml_config.get(category, {})

    def _convert_value(self, value_str: str, data_type: str) -> Any:
        """Convert string value to appropriate type"""
        if data_type == 'integer':
            return int(value_str)
        elif data_type == 'float':
            return float(value_str)
        elif data_type == 'boolean':
            return value_str.lower() in ('true', '1', 'yes', 'on')
        elif data_type == 'json':
            import json
            return json.loads(value_str)
        else:
            return value_str

    def _infer_data_type(self, value: Any) -> str:
        """Infer data type from value"""
        if isinstance(value, bool):
            return 'boolean'
        elif isinstance(value, int):
            return 'integer'
        elif isinstance(value, float):
            return 'float'
        elif isinstance(value, (dict, list)):
            return 'json'
        else:
            return 'string'

    async def reload_cache(self):
        """Reload configuration cache from database"""
        self._config_cache.clear()
        if self.db_pool:
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch("SELECT key, value, data_type FROM system_config")
                for row in rows:
                    self._config_cache[row['key']] = self._convert_value(
                        row['value'], row['data_type']
                    )

    async def close(self):
        """Close database connections"""
        if self.db_pool:
            await self.db_pool.close()


# Global configuration manager instance
config = ConfigManager()


async def init_config(config_file: str = None, db_url: str = None):
    """Initialize global configuration manager"""
    global config
    if config_file:
        config = ConfigManager(config_file, db_url)
    if db_url:
        await config.initialize_db()