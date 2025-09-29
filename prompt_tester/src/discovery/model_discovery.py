import requests
import json
from typing import List, Dict

class ModelDiscovery:
    def __init__(self, lm_studio_url: str = "http://localhost:1234"):
        self.base_url = lm_studio_url
        
    def discover_conversational_models(self) -> List[Dict]:
        """Discover conversational models from LM Studio"""
        try:
            response = requests.get(f"{self.base_url}/v1/models", timeout=10)
            response.raise_for_status()
            
            models_data = response.json()
            conversational_models = []
            
            for model in models_data.get("data", []):
                model_id = model.get("id", "")
                # Skip embedding models, include everything else
                if "embed" not in model_id.lower():
                    conversational_models.append({
                        "id": model_id,
                        "object": model.get("object", ""),
                        "created": model.get("created", 0),
                        "owned_by": model.get("owned_by", "")
                    })
            
            return conversational_models
            
        except Exception as e:
            print(f"Error discovering models: {e}")
            return []
    
    def test_model_availability(self, model_id: str) -> bool:
        """Test if a specific model is available and responsive"""
        try:
            test_payload = {
                "model": model_id,
                "messages": [{"role": "user", "content": "test"}],
                "max_tokens": 5,
                "temperature": 0.1
            }
            
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                json=test_payload,
                timeout=30
            )
            
            return response.status_code == 200
            
        except Exception:
            return False