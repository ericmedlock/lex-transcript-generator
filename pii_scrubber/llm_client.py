"""
LLM Client for PII Redaction
"""
import json
import requests
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class LLMUnavailableError(Exception):
    """Raised when LLM endpoint is unavailable or fails"""
    pass

def get_first_chat_model(endpoint: str, timeout: int) -> str:
    """Get first available conversational model from LM Studio"""
    try:
        models_url = endpoint.replace('/chat/completions', '/models')
        response = requests.get(models_url, timeout=timeout)
        response.raise_for_status()
        
        data = response.json()
        models = data.get('data', [])
        
        # Filter for conversational models (exclude embedding models)
        chat_models = []
        for model in models:
            model_id = model.get('id', '')
            if not any(keyword in model_id.lower() for keyword in ['embed', 'embedding', 'bge-', 'e5-']):
                chat_models.append(model_id)
        
        if not chat_models:
            raise LLMUnavailableError("No conversational models available")
        
        return chat_models[0]
        
    except Exception as e:
        raise LLMUnavailableError(f"Failed to get model list: {e}")

def redact_with_llm(text: str, endpoint: str, model: str, timeout: int) -> str:
    """
    Redact PII using local LLM endpoint.
    
    Args:
        text: Input text to redact
        endpoint: LLM API endpoint
        model: Model name (ignored, auto-detected)
        timeout: Request timeout in seconds
    
    Returns:
        Redacted text
        
    Raises:
        LLMUnavailableError: If LLM is unavailable or fails
    """
    # Auto-detect first available chat model
    actual_model = get_first_chat_model(endpoint, timeout)
    
    prompt = (
        "You are a PII redaction tool. Replace personal information with placeholders: "
        "<NAME> for names, <PHONE> for phone numbers, <EMAIL> for emails, "
        "<DATE> for dates, <ADDRESS> for addresses, <ID> for ID numbers, "
        "<INSURANCEID> for insurance IDs.\n\n"
        "IMPORTANT: Return ONLY the redacted text. No thinking, no explanations, no commentary.\n\n"
        f"Text to redact: {text}\n\n"
        "Redacted text:"
    )
    
    # Use OpenAI-compatible format for LM Studio
    payload = {
        "model": actual_model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "max_tokens": len(text) + 100
    }
    
    try:
        response = requests.post(endpoint, json=payload, timeout=timeout)
        response.raise_for_status()
        
        data = response.json()
        
        # Handle different LLM API response formats
        if 'choices' in data and data['choices']:
            # OpenAI-compatible format (LM Studio)
            redacted_text = data['choices'][0].get('message', {}).get('content', '').strip()
        elif 'response' in data:
            # Ollama format
            redacted_text = data['response'].strip()
        elif 'text' in data:
            # Generic text response
            redacted_text = data['text'].strip()
        else:
            logger.error(f"Unexpected LLM response format: {data}")
            raise LLMUnavailableError("Unexpected response format from LLM")
        
        if not redacted_text:
            raise LLMUnavailableError("Empty response from LLM")
        
        return redacted_text
        
    except requests.exceptions.ConnectionError:
        raise LLMUnavailableError(f"Cannot connect to LLM endpoint: {endpoint}")
    except requests.exceptions.Timeout:
        raise LLMUnavailableError(f"LLM request timed out after {timeout}s")
    except requests.exceptions.HTTPError as e:
        # Check if it's a 400 error due to no model loaded
        if response.status_code == 400:
            raise LLMUnavailableError(f"LLM model not loaded or invalid request (check LM Studio has a model loaded)")
        raise LLMUnavailableError(f"LLM HTTP error: {e}")
    except json.JSONDecodeError:
        raise LLMUnavailableError("Invalid JSON response from LLM")
    except Exception as e:
        raise LLMUnavailableError(f"LLM request failed: {e}")