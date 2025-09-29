"""
PII Scrubbing Engine
"""
import re
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

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
    'NAME': r'\b([A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})+)\b'
}

# Context patterns for ID detection
ID_CONTEXTS = [
    r'(?:policy|member|MRN|account|ID|number)\s*:?\s*([A-Z0-9]{6,12})\b',
    r'\b([A-Z0-9]{6,12})\s*(?:policy|member|MRN|account|ID|number)',
    r'insurance\s+(?:ID|number)\s*:?\s*([A-Z0-9]{6,12})\b'
]

def detect_pii_regex(text: str) -> Dict[str, list]:
    """Detect PII using regex patterns. Returns matches by type."""
    matches = {}
    
    # Standard patterns
    for pii_type, pattern in PII_PATTERNS.items():
        found = re.findall(pattern, text, re.IGNORECASE)
        if pii_type == 'NAME':
            # Filter out common words
            found = [match for match in found if match.lower() not in NAME_ALLOWLIST]
        matches[pii_type] = found
    
    # ID patterns with context
    id_matches = []
    for pattern in ID_CONTEXTS:
        id_matches.extend(re.findall(pattern, text, re.IGNORECASE))
    matches['ID'] = id_matches
    
    return matches

def scrub_text_regex(text: str, placeholder_style: str = "angle") -> str:
    """Scrub PII using regex patterns."""
    result = text
    
    # Choose placeholder format
    if placeholder_style == "bracket":
        fmt = "[{}]"
    else:  # angle (default)
        fmt = "<{}>"
    
    # Apply replacements in order of specificity
    patterns_order = ['PHONE', 'EMAIL', 'DATE', 'ADDRESS', 'NAME']
    
    for pii_type in patterns_order:
        pattern = PII_PATTERNS[pii_type]
        placeholder = fmt.format(pii_type)
        
        if pii_type == 'NAME':
            # Special handling for names - check allowlist
            def name_replacer(match):
                name = match.group(1) if match.groups() else match.group(0)
                if name.lower() not in NAME_ALLOWLIST:
                    return placeholder
                return name
            result = re.sub(pattern, name_replacer, result, flags=re.IGNORECASE)
        else:
            result = re.sub(pattern, placeholder, result, flags=re.IGNORECASE)
    
    # Handle ID patterns with context
    for pattern in ID_CONTEXTS:
        result = re.sub(pattern, lambda m: m.group(0).replace(m.group(1), fmt.format("ID")), 
                       result, flags=re.IGNORECASE)
    
    return result

def scrub_text(text: str, mode: str, strategy: str, cfg: Dict[str, Any]) -> str:
    """
    Main PII scrubbing function.
    
    Args:
        text: Input text to scrub
        mode: "safe" or "raw"
        strategy: "llm", "regex", or "off"
        cfg: Configuration dictionary
    
    Returns:
        Scrubbed text
    """
    if mode == "raw" or strategy == "off":
        return text
    
    if strategy == "llm":
        try:
            from .llm_client import redact_with_llm
            endpoint = cfg.get('llm', {}).get('endpoint', 'http://127.0.0.1:11434/api/generate')
            model = cfg.get('llm', {}).get('model', 'redactor-7b-gguf')
            timeout = cfg.get('llm', {}).get('timeout_s', 20)
            
            return redact_with_llm(text, endpoint, model, timeout)
        except Exception as e:
            logger.warning(f"LLM scrubbing failed: {e}")
            # Fallback to regex if LLM fails and not explicitly requested
            if cfg.get('fallback_to_regex', True):
                logger.info("Falling back to regex scrubbing")
                strategy = "regex"
            else:
                raise
    
    if strategy == "regex":
        placeholder_style = cfg.get('scrub', {}).get('placeholder_style', 'angle')
        return scrub_text_regex(text, placeholder_style)
    
    return text