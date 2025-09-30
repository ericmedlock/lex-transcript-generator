"""
Endpoint Discovery - Utilities for discovering and managing LLM endpoints
"""

import requests
from typing import List, Dict, Optional


class EndpointDiscovery:
    """Utilities for discovering and testing LLM endpoints"""
    
    @staticmethod
    def discover_local_endpoints(ports: Optional[List[int]] = None, timeout: int = 2) -> List[str]:
        """
        Discover local LLM endpoints
        
        Args:
            ports: List of ports to check (default: common LLM ports)
            timeout: Request timeout in seconds
            
        Returns:
            List of discovered endpoint URLs
        """
        if ports is None:
            ports = [8000, 8080, 11434, 5000, 7860, 1234]
        
        endpoints = []
        
        for port in ports:
            try:
                response = requests.get(f"http://localhost:{port}/v1/models", timeout=timeout)
                if response.status_code == 200:
                    endpoints.append(f"http://localhost:{port}/v1")
            except:
                continue
        
        return endpoints
    
    @staticmethod
    def test_endpoint(endpoint_url: str, timeout: int = 5) -> Dict[str, any]:
        """
        Test if an endpoint is working
        
        Args:
            endpoint_url: Endpoint URL to test
            timeout: Request timeout in seconds
            
        Returns:
            Dict with keys: available, models, error
        """
        try:
            # Test models endpoint
            response = requests.get(f"{endpoint_url}/models", timeout=timeout)
            if response.status_code == 200:
                models = response.json().get("data", [])
                return {"available": True, "models": models, "error": None}
            else:
                return {"available": False, "models": [], "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            return {"available": False, "models": [], "error": str(e)}
    
    @staticmethod
    def get_endpoint_info(endpoint_url: str, timeout: int = 5) -> Dict[str, any]:
        """
        Get detailed information about an endpoint
        
        Args:
            endpoint_url: Endpoint URL
            timeout: Request timeout in seconds
            
        Returns:
            Dict with endpoint information
        """
        info = {
            "url": endpoint_url,
            "available": False,
            "models": [],
            "error": None
        }
        
        try:
            # Test basic availability
            response = requests.get(f"{endpoint_url}/models", timeout=timeout)
            if response.status_code == 200:
                info["available"] = True
                models_data = response.json().get("data", [])
                info["models"] = [model.get("id", "unknown") for model in models_data]
            else:
                info["error"] = f"HTTP {response.status_code}"
                
        except Exception as e:
            info["error"] = str(e)
        
        return info