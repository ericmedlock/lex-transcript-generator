"""
LLM Provider - Three-tier LLM system with automatic failover

Supports:
- Local LLM endpoints (LM Studio, Ollama)
- Network LLM endpoints
- OpenAI API
"""

import json
import os
import requests
from typing import Dict, List, Optional, Any
from openai import OpenAI


class LLMProvider:
    """Three-tier LLM provider with automatic endpoint discovery and failover"""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize LLM provider
        
        Args:
            config: Configuration dict with optional keys:
                - openai_api_key: OpenAI API key (or use OPENAI_API_KEY env var)
                - network_url: Network LLM endpoint URL
                - timeout: Request timeout in seconds (default: 30)
                - model: Default model name (default: gpt-3.5-turbo)
        """
        self.config = config or {}
        self.timeout = self.config.get('timeout', 30)
        self.default_model = self.config.get('model', 'gpt-3.5-turbo')
        
        # Initialize OpenAI client
        openai_key = self.config.get('openai_api_key') or os.getenv('OPENAI_API_KEY')
        self.openai_client = OpenAI(api_key=openai_key) if openai_key else None
        
        # Cache discovered endpoints
        self._local_endpoints = None
        
    def discover_local_endpoints(self) -> List[str]:
        """Discover local LLM endpoints"""
        if self._local_endpoints is not None:
            return self._local_endpoints
            
        endpoints = []
        ports = [8000, 8080, 11434, 5000, 7860, 1234]
        
        for port in ports:
            try:
                response = requests.get(f"http://localhost:{port}/v1/models", timeout=2)
                if response.status_code == 200:
                    endpoints.append(f"http://localhost:{port}/v1")
            except:
                continue
        
        self._local_endpoints = endpoints
        return endpoints
    
    def generate(self, 
                prompt: str, 
                provider: str = "auto",
                model: Optional[str] = None,
                temperature: float = 0.7,
                max_tokens: Optional[int] = None) -> Dict[str, Any]:
        """
        Generate text using specified provider
        
        Args:
            prompt: Input prompt
            provider: Provider type ("local", "network", "openai", "auto")
            model: Model name (uses default if not specified)
            temperature: Generation temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Dict with keys: content, provider_used, error
        """
        if provider == "auto":
            # Try providers in order: local -> network -> openai
            for provider_type in ["local", "network", "openai"]:
                result = self.generate(prompt, provider_type, model, temperature, max_tokens)
                if not result.get("error"):
                    return result
            
            return {"content": None, "provider_used": None, "error": "All providers failed"}
        
        elif provider == "local":
            return self._generate_local(prompt, model, temperature, max_tokens)
        elif provider == "network":
            return self._generate_network(prompt, model, temperature, max_tokens)
        elif provider == "openai":
            return self._generate_openai(prompt, model, temperature, max_tokens)
        else:
            return {"content": None, "provider_used": None, "error": f"Unknown provider: {provider}"}
    
    def _generate_local(self, prompt: str, model: Optional[str], temperature: float, max_tokens: Optional[int]) -> Dict[str, Any]:
        """Generate using local LLM endpoint"""
        endpoints = self.discover_local_endpoints()
        if not endpoints:
            return {"content": None, "provider_used": "local", "error": "No local LLM endpoints found"}
        
        return self._generate_with_endpoint(endpoints[0], prompt, model, temperature, max_tokens, "local")
    
    def _generate_network(self, prompt: str, model: Optional[str], temperature: float, max_tokens: Optional[int]) -> Dict[str, Any]:
        """Generate using network LLM endpoint"""
        network_url = self.config.get('network_url')
        if not network_url:
            return {"content": None, "provider_used": "network", "error": "No network URL configured"}
        
        return self._generate_with_endpoint(network_url, prompt, model, temperature, max_tokens, "network")
    
    def _generate_openai(self, prompt: str, model: Optional[str], temperature: float, max_tokens: Optional[int]) -> Dict[str, Any]:
        """Generate using OpenAI API"""
        if not self.openai_client:
            return {"content": None, "provider_used": "openai", "error": "No OpenAI API key configured"}
        
        try:
            response = self.openai_client.chat.completions.create(
                model=model or "gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            content = response.choices[0].message.content.strip()
            return {"content": content, "provider_used": "openai", "error": None}
            
        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg or "invalid_api_key" in error_msg:
                error_msg = "Invalid OpenAI API key"
            return {"content": None, "provider_used": "openai", "error": error_msg}
    
    def _generate_with_endpoint(self, endpoint_url: str, prompt: str, model: Optional[str], 
                               temperature: float, max_tokens: Optional[int], provider_name: str) -> Dict[str, Any]:
        """Generate using OpenAI-compatible endpoint"""
        try:
            payload = {
                "model": model or self.default_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature
            }
            
            if max_tokens:
                payload["max_tokens"] = max_tokens
            
            response = requests.post(
                f"{endpoint_url}/chat/completions",
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                return {
                    "content": None, 
                    "provider_used": provider_name, 
                    "error": f"HTTP {response.status_code}: {response.text[:100]}"
                }
            
            result = response.json()
            content = result["choices"][0]["message"]["content"].strip()
            return {"content": content, "provider_used": provider_name, "error": None}
            
        except Exception as e:
            return {"content": None, "provider_used": provider_name, "error": str(e)}
    
    def is_available(self, provider: str) -> bool:
        """Check if a provider is available"""
        if provider == "local":
            return len(self.discover_local_endpoints()) > 0
        elif provider == "network":
            return bool(self.config.get('network_url'))
        elif provider == "openai":
            return self.openai_client is not None
        else:
            return False
    
    def get_available_providers(self) -> List[str]:
        """Get list of available providers"""
        providers = []
        if self.is_available("local"):
            providers.append("local")
        if self.is_available("network"):
            providers.append("network")
        if self.is_available("openai"):
            providers.append("openai")
        return providers