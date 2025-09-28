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

def redact_with_llm(text: str, endpoint: str, model: str, timeout: int) -> str:
    """
    Redact PII using local LLM endpoint.
    
    Args:
        text: Input text to redact
        endpoint: LLM API endpoint
        model: Model name
        timeout: Request timeout in seconds
    
    Returns:
        Redacted text
        
    Raises:
        LLMUnavailableError: If LLM is unavailable or fails
    """
    prompt = (
        "Redact PII in the following text by replacing spans with placeholders "
        "<NAME>, <PHONE>, <EMAIL>, <DATE>, <ADDRESS>, <ID>, <INSURANCEID>. "
        "Keep everything else unchanged.\n\n"
        f"TEXT:\n<<<{text}>>>\n\n"
        "REDACTED:"
    )
    
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    
    try:
        response = requests.post(endpoint, json=payload, timeout=timeout)
        response.raise_for_status()
        
        data = response.json()
        
        # Handle different LLM API response formats
        if 'response' in data:
            # Ollama format
            redacted_text = data['response'].strip()
        elif 'choices' in data and data['choices']:
            # OpenAI-compatible format
            redacted_text = data['choices'][0].get('message', {}).get('content', '').strip()
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
        raise LLMUnavailableError(f"LLM HTTP error: {e}")
    except json.JSONDecodeError:
        raise LLMUnavailableError("Invalid JSON response from LLM")
    except Exception as e:
        raise LLMUnavailableError(f"LLM request failed: {e}")