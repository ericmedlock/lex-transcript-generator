"""
LLM Provider Module

Three-tier LLM system supporting:
- Local LLM endpoints (LM Studio, Ollama)
- Network LLM endpoints 
- OpenAI API
"""

from .provider import LLMProvider
from .endpoints import EndpointDiscovery

__all__ = ["LLMProvider", "EndpointDiscovery"]