"""
PII Processor - Comprehensive PII detection and scrubbing

Supports LLM-based and regex-based PII detection with configurable strategies.
"""

import re
import logging
from typing import Dict, Any, Optional, List, Union
from pathlib import Path

logger = logging.getLogger(__name__)


class PIIProcessor:
    """Handle PII detection and scrubbing with multiple strategies"""
    
    # Common words to exclude from name detection
    NAME_ALLOWLIST = {
        'agent', 'customer', 'doctor', 'nurse', 'patient', 'sir', 'madam', 'mister', 'miss',
        'hello', 'thank', 'please', 'sorry', 'okay', 'yes', 'no', 'sure', 'right', 'good',
        'morning', 'afternoon', 'evening', 'today', 'tomorrow', 'yesterday', 'monday',
        'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday', 'like', 'make',
        'appointment', 'help', 'need', 'see', 'pull', 'record', 'moment', 'available',
        'work', 'perfect', 'fantastic', 'get', 'scheduled', 'confirm', 'birth', 'all',
        'welcome', 'have', 'day', 'just', 'can', 'what', 'type', 'else', 'anything'
    }
    
    # Regex patterns for PII detection
    PII_PATTERNS = {
        'PHONE': r'\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b',
        'EMAIL': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b',
        'DATE': r'\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{2,4})\b',
        'ADDRESS': r'\b\d{1,5}\s+[A-Za-z0-9.\s]+(?:St|Street|Rd|Road|Ave|Avenue|Blvd|Lane|Ln|Dr|Drive)\b',
        'NAME': r'\b([A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})+)\b',
        'SSN': r'\b\d{3}-\d{2}-\d{4}\b',
        'CREDIT_CARD': r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'
    }
    
    # Context patterns for ID detection
    ID_CONTEXTS = [
        r'(?:policy|member|MRN|account|ID|number)\s*:?\s*([A-Z0-9]{6,12})\b',
        r'\b([A-Z0-9]{6,12})\s*(?:policy|member|MRN|account|ID|number)',
        r'insurance\s+(?:ID|number)\s*:?\s*([A-Z0-9]{6,12})\b'
    ]
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize PII processor
        
        Args:
            config: Configuration dict with optional keys:
                - default_strategy: 'llm', 'regex', or 'off' (default: 'regex')
                - placeholder_style: 'angle' or 'bracket' (default: 'angle')
                - fallback_to_regex: bool (default: True)
                - llm_endpoint: LLM endpoint URL for LLM strategy
                - llm_timeout: LLM request timeout in seconds (default: 20)
        """
        self.config = config or {}
        self.default_strategy = self.config.get('default_strategy', 'regex')
        self.placeholder_style = self.config.get('placeholder_style', 'angle')
        self.fallback_to_regex = self.config.get('fallback_to_regex', True)
        
        # LLM configuration
        self.llm_endpoint = self.config.get('llm_endpoint')
        self.llm_timeout = self.config.get('llm_timeout', 20)
        
        # Check LLM availability
        self._llm_available = self._check_llm_availability()
    
    def _check_llm_availability(self) -> bool:
        """Check if LLM endpoint is available"""
        if not self.llm_endpoint:
            return False
            
        try:
            import requests
            # Test endpoint availability
            models_url = self.llm_endpoint.replace('/chat/completions', '/models')
            response = requests.get(models_url, timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def scrub_text(self, text: str, strategy: Optional[str] = None) -> str:
        """
        Scrub PII from text
        
        Args:
            text: Text to scrub
            strategy: 'llm', 'regex', or 'off' (uses default if not specified)
            
        Returns:
            Scrubbed text
        """
        if strategy is None:
            strategy = self.default_strategy
        
        if strategy == 'off':
            return text
        elif strategy == 'llm':
            return self._scrub_with_llm(text)
        elif strategy == 'regex':
            return self._scrub_with_regex(text)
        else:
            logger.warning(f"Unknown strategy '{strategy}', using regex")
            return self._scrub_with_regex(text)
    
    def _scrub_with_llm(self, text: str) -> str:
        """Scrub PII using LLM"""
        if not self._llm_available:
            if self.fallback_to_regex:
                logger.warning("LLM not available, falling back to regex")
                return self._scrub_with_regex(text)
            else:
                raise ValueError("LLM strategy requested but not available")
        
        try:
            return self._redact_with_llm(text)
        except Exception as e:
            logger.error(f"LLM scrubbing failed: {e}")
            if self.fallback_to_regex:
                logger.info("Falling back to regex scrubbing")
                return self._scrub_with_regex(text)
            raise
    
    def _scrub_with_regex(self, text: str) -> str:
        """Scrub PII using regex patterns"""
        result = text
        
        # Choose placeholder format
        if self.placeholder_style == "bracket":
            fmt = "[{}]"
        else:  # angle (default)
            fmt = "<{}>"
        
        # Apply replacements in order of specificity
        patterns_order = ['PHONE', 'EMAIL', 'SSN', 'CREDIT_CARD', 'DATE', 'ADDRESS', 'NAME']
        
        for pii_type in patterns_order:
            if pii_type not in self.PII_PATTERNS:
                continue
                
            pattern = self.PII_PATTERNS[pii_type]
            placeholder = fmt.format(pii_type)
            
            if pii_type == 'NAME':
                # Special handling for names - check allowlist
                def name_replacer(match):
                    name = match.group(1) if match.groups() else match.group(0)
                    if name.lower() not in self.NAME_ALLOWLIST:
                        return placeholder
                    return name
                result = re.sub(pattern, name_replacer, result, flags=re.IGNORECASE)
            else:
                result = re.sub(pattern, placeholder, result, flags=re.IGNORECASE)
        
        # Handle ID patterns with context
        for pattern in self.ID_CONTEXTS:
            result = re.sub(pattern, lambda m: m.group(0).replace(m.group(1), fmt.format("ID")), 
                           result, flags=re.IGNORECASE)
        
        return result
    
    def detect_pii(self, text: str) -> Dict[str, int]:
        """
        Detect PII in text and return counts by type
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with PII type counts
        """
        counts = {}
        
        # Standard patterns
        for pii_type, pattern in self.PII_PATTERNS.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if pii_type == 'NAME':
                # Filter out common words
                matches = [match for match in matches if match.lower() not in self.NAME_ALLOWLIST]
            if matches:
                counts[pii_type] = len(matches)
        
        # ID patterns with context
        id_matches = []
        for pattern in self.ID_CONTEXTS:
            id_matches.extend(re.findall(pattern, text, re.IGNORECASE))
        if id_matches:
            counts['ID'] = len(id_matches)
        
        return counts
    
    def batch_scrub_texts(self, texts: List[str], strategy: Optional[str] = None) -> List[str]:
        """
        Scrub multiple texts efficiently
        
        Args:
            texts: List of texts to scrub
            strategy: Scrubbing strategy to use
            
        Returns:
            List of scrubbed texts in same order
        """
        if strategy is None:
            strategy = self.default_strategy
        
        if strategy == 'off':
            return texts
        elif strategy == 'llm' and self._llm_available:
            try:
                return self._batch_redact_with_llm(texts)
            except Exception as e:
                logger.error(f"Batch LLM scrubbing failed: {e}")
                if self.fallback_to_regex:
                    logger.info("Falling back to regex scrubbing")
                    return [self._scrub_with_regex(text) for text in texts]
                raise
        else:
            # Use regex for individual texts
            return [self._scrub_with_regex(text) for text in texts]
    
    def _redact_with_llm(self, text: str) -> str:
        """Redact PII using LLM endpoint"""
        import requests
        import json
        
        # Get first available chat model
        actual_model = self._get_first_chat_model()
        
        prompt = (
            "You are a PII redaction tool. Replace personal information with placeholders: "
            "<NAME> for names, <PHONE> for phone numbers, <EMAIL> for emails, "
            "<DATE> for dates, <ADDRESS> for addresses, <ID> for ID numbers, "
            "<INSURANCEID> for insurance IDs.\n\n"
            "IMPORTANT: Return ONLY the redacted text. No thinking, no explanations, no commentary.\n\n"
            f"Text to redact: {text}\n\n"
            "Redacted text:"
        )
        
        payload = {
            "model": actual_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": len(text) + 100
        }
        
        response = requests.post(self.llm_endpoint, json=payload, timeout=self.llm_timeout)
        response.raise_for_status()
        
        data = response.json()
        
        # Handle different response formats
        if 'choices' in data and data['choices']:
            return data['choices'][0].get('message', {}).get('content', '').strip()
        elif 'response' in data:
            return data['response'].strip()
        elif 'text' in data:
            return data['text'].strip()
        else:
            raise ValueError("Unexpected LLM response format")
    
    def _batch_redact_with_llm(self, texts: List[str]) -> List[str]:
        """Batch redact multiple texts using LLM"""
        if not texts:
            return []
        
        import requests
        import json
        
        actual_model = self._get_first_chat_model()
        
        # Create batch prompt
        batch_prompt = (
            "You are a PII redaction tool. Replace personal information with placeholders: "
            "<NAME> for names, <PHONE> for phone numbers, <EMAIL> for emails, "
            "<DATE> for dates, <ADDRESS> for addresses, <ID> for ID numbers, "
            "<INSURANCEID> for insurance IDs.\n\n"
            "IMPORTANT: Return ONLY the redacted texts in the same order, separated by '---NEXT---'. "
            "No thinking, no explanations, no commentary.\n\n"
            "Texts to redact:\n\n"
        )
        
        for i, text in enumerate(texts, 1):
            batch_prompt += f"Text {i}: {text}\n\n"
        
        batch_prompt += "Redacted texts (separated by '---NEXT---'):"
        
        payload = {
            "model": actual_model,
            "messages": [{"role": "user", "content": batch_prompt}],
            "temperature": 0.1,
            "max_tokens": sum(len(text) for text in texts) + 500
        }
        
        response = requests.post(self.llm_endpoint, json=payload, timeout=self.llm_timeout * 2)
        response.raise_for_status()
        
        data = response.json()
        
        # Handle response
        if 'choices' in data and data['choices']:
            batch_response = data['choices'][0].get('message', {}).get('content', '').strip()
        elif 'response' in data:
            batch_response = data['response'].strip()
        elif 'text' in data:
            batch_response = data['text'].strip()
        else:
            raise ValueError("Unexpected LLM response format")
        
        # Parse batch response
        redacted_texts = batch_response.split('---NEXT---')
        redacted_texts = [text.strip() for text in redacted_texts]
        
        # Validate response count
        if len(redacted_texts) != len(texts):
            logger.warning(f"Expected {len(texts)} responses, got {len(redacted_texts)}. Using individual processing.")
            return [self._redact_with_llm(text) for text in texts]
        
        return redacted_texts
    
    def _get_first_chat_model(self) -> str:
        """Get first available conversational model"""
        import requests
        
        models_url = self.llm_endpoint.replace('/chat/completions', '/models')
        response = requests.get(models_url, timeout=self.llm_timeout)
        response.raise_for_status()
        
        data = response.json()
        models = data.get('data', [])
        
        # Filter for conversational models
        chat_models = []
        for model in models:
            model_id = model.get('id', '')
            if not any(keyword in model_id.lower() for keyword in ['embed', 'embedding', 'bge-', 'e5-']):
                chat_models.append(model_id)
        
        if not chat_models:
            raise ValueError("No conversational models available")
        
        return chat_models[0]