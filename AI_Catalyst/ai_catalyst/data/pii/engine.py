"""
PII Engine - Core PII detection and scrubbing utilities

Low-level functions for PII pattern matching and text processing.
"""

import re
from typing import Dict, List, Any


class PIIEngine:
    """Core PII detection and scrubbing engine"""
    
    @staticmethod
    def detect_pii_patterns(text: str, patterns: Dict[str, str]) -> Dict[str, List[str]]:
        """
        Detect PII using provided patterns
        
        Args:
            text: Text to analyze
            patterns: Dict of pattern_name -> regex_pattern
            
        Returns:
            Dict of pattern_name -> list of matches
        """
        matches = {}
        
        for pattern_name, pattern in patterns.items():
            found = re.findall(pattern, text, re.IGNORECASE)
            if found:
                matches[pattern_name] = found
        
        return matches
    
    @staticmethod
    def replace_pii_patterns(text: str, patterns: Dict[str, str], placeholder_format: str = "<{}>") -> str:
        """
        Replace PII using provided patterns
        
        Args:
            text: Text to process
            patterns: Dict of pattern_name -> regex_pattern
            placeholder_format: Format string for placeholders (e.g., "<{}>" or "[{}]")
            
        Returns:
            Text with PII replaced by placeholders
        """
        result = text
        
        for pattern_name, pattern in patterns.items():
            placeholder = placeholder_format.format(pattern_name)
            result = re.sub(pattern, placeholder, result, flags=re.IGNORECASE)
        
        return result
    
    @staticmethod
    def filter_matches_by_allowlist(matches: List[str], allowlist: set) -> List[str]:
        """
        Filter matches against an allowlist
        
        Args:
            matches: List of matched strings
            allowlist: Set of allowed strings (case-insensitive)
            
        Returns:
            Filtered list of matches
        """
        return [match for match in matches if match.lower() not in allowlist]
    
    @staticmethod
    def extract_context_patterns(text: str, context_patterns: List[str]) -> List[str]:
        """
        Extract values using context-aware patterns
        
        Args:
            text: Text to analyze
            context_patterns: List of regex patterns with capture groups
            
        Returns:
            List of extracted values
        """
        matches = []
        
        for pattern in context_patterns:
            found = re.findall(pattern, text, re.IGNORECASE)
            matches.extend(found)
        
        return matches