"""
AI_Catalyst - Reusable AI Components Framework

A collection of proven, reusable components for AI applications including:
- Three-tier LLM providers (local/network/OpenAI)
- PII detection and scrubbing
- File processing and data handling
- Database patterns and configuration management
- System monitoring and performance tuning
"""

__version__ = "0.1.0"
__author__ = "Eric Medlock"

# Core imports for easy access
from .llm import LLMProvider
from .data.processors import FileProcessor
from .data.pii import PIIProcessor
from .config import ConfigManager
from .database import DatabaseManager

__all__ = [
    "LLMProvider",
    "FileProcessor", 
    "PIIProcessor",
    "ConfigManager",
    "DatabaseManager"
]