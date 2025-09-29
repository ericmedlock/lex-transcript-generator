import requests
import time
import json
from typing import Dict, Tuple

class PromptExecutor:
    def __init__(self, lm_studio_url: str = "http://localhost:1234"):
        self.base_url = lm_studio_url
    
    def execute_prompt(self, model_id: str, prompt: str) -> Tuple[str, Dict]:
        """Execute prompt and return response with timing metrics"""
        start_time = time.time()
        
        payload = {
            "model": model_id,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2000,
            "temperature": 0.7,
            "stream": False
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                timeout=300  # 5 minute timeout
            )
            response.raise_for_status()
            
            end_time = time.time()
            response_data = response.json()
            
            # Extract response content
            content = response_data["choices"][0]["message"]["content"]
            
            # Calculate metrics
            total_time = end_time - start_time
            usage = response_data.get("usage", {})
            total_tokens = usage.get("total_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            
            tokens_per_second = completion_tokens / total_time if total_time > 0 else 0
            
            metrics = {
                "total_time": total_time,
                "tokens_per_second": tokens_per_second,
                "total_tokens": total_tokens,
                "completion_tokens": completion_tokens,
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "success": True,
                "error": None
            }
            
            return content, metrics
            
        except Exception as e:
            end_time = time.time()
            metrics = {
                "total_time": end_time - start_time,
                "tokens_per_second": 0,
                "total_tokens": 0,
                "completion_tokens": 0,
                "prompt_tokens": 0,
                "success": False,
                "error": str(e)
            }
            return "", metrics