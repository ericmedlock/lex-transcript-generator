"""
Configuration Module

Database-first configuration with YAML fallbacks and hierarchical management.
"""

from .manager import ConfigManager

__all__ = ["ConfigManager"]