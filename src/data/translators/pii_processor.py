#!/usr/bin/env python3
"""
PII Processor - Wrapper for PII scrubbing functionality
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class PIIProcessor:
    """Handle PII scrubbing with fallback strategies"""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config = self._load_config(config_path)
        self._pii_available = self._check_pii_availability()
    
    def _load_config(self, config_path: Optional[Path]) -> Dict[str, Any]:
        """Load PII configuration"""
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent.parent / "pii_scrubber" / "config.yaml"
        
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"PII config not found at {config_path}, using defaults")
            return {
                'default_mode': 'safe',
                'default_strategy': 'regex',
                'fallback_to_regex': True,
                'scrub': {'placeholder_style': 'angle'}
            }
    
    def _check_pii_availability(self) -> bool:
        """Check if PII scrubber is available"""
        try:
            from pii_scrubber.engine import scrub_text
            return True
        except ImportError:
            logger.warning("PII scrubber not available, will use basic regex fallback")
            return False
    
    def scrub_text(self, text: str, mode: str = None, strategy: str = None) -> str:
        """
        Scrub PII from text
        
        Args:
            text: Text to scrub
            mode: 'safe' or 'raw'
            strategy: 'llm', 'regex', or 'off'
            
        Returns:
            Scrubbed text
        """
        if mode is None:
            mode = self.config.get('default_mode', 'safe')
        if strategy is None:
            strategy = self.config.get('default_strategy', 'regex')
        
        # Raw mode or off strategy - return original
        if mode == 'raw' or strategy == 'off':
            return text
        
        # Use PII scrubber if available
        if self._pii_available:
            try:
                from pii_scrubber.engine import scrub_text as pii_scrub_text
                return pii_scrub_text(text, mode, strategy, self.config)
            except Exception as e:
                logger.error(f"PII scrubbing failed: {e}")
                if self.config.get('fallback_to_regex', True):
                    return self._basic_regex_scrub(text)
                raise
        else:
            # Fallback to basic regex
            return self._basic_regex_scrub(text)
    
    def _basic_regex_scrub(self, text: str) -> str:
        """Basic regex-based PII scrubbing as fallback"""
        import re
        
        # Basic patterns for common PII
        patterns = {
            'PHONE': r'\b(?:\+?1[-.\s]?)?(?:\(?[0-9]{3}\)?[-.\s]?)?[0-9]{3}[-.\s]?[0-9]{4}\b',
            'EMAIL': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b',
            'DATE': r'\b(?:[0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+[0-9]{1,2},?\s+[0-9]{2,4})\b',
            'SSN': r'\b[0-9]{3}-[0-9]{2}-[0-9]{4}\b',
            'CREDIT_CARD': r'\b[0-9]{4}[-\s]?[0-9]{4}[-\s]?[0-9]{4}[-\s]?[0-9]{4}\b'
        }
        
        result = text
        placeholder_style = self.config.get('scrub', {}).get('placeholder_style', 'angle')
        
        if placeholder_style == 'bracket':
            fmt = '[{}]'
        else:
            fmt = '<{}>'
        
        for pii_type, pattern in patterns.items():
            result = re.sub(pattern, fmt.format(pii_type), result, flags=re.IGNORECASE)
        
        return result
    
    def detect_pii(self, text: str) -> Dict[str, int]:
        """
        Detect PII in text and return counts by type
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with PII type counts
        """
        if self._pii_available:
            try:
                from pii_scrubber.engine import detect_pii_regex
                pii_matches = detect_pii_regex(text)
                return {pii_type: len(matches) for pii_type, matches in pii_matches.items() if matches}
            except Exception as e:
                logger.error(f"PII detection failed: {e}")
        
        # Fallback detection
        return self._basic_pii_detection(text)
    
    def _basic_pii_detection(self, text: str) -> Dict[str, int]:
        """Basic PII detection as fallback"""
        import re
        
        patterns = {
            'PHONE': r'\b(?:\+?1[-.\s]?)?(?:\(?[0-9]{3}\)?[-.\s]?)?[0-9]{3}[-.\s]?[0-9]{4}\b',
            'EMAIL': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b',
            'DATE': r'\b(?:[0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4})\b',
            'SSN': r'\b[0-9]{3}-[0-9]{2}-[0-9]{4}\b'
        }
        
        counts = {}
        for pii_type, pattern in patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                counts[pii_type] = len(matches)
        
        return counts