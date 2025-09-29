#!/usr/bin/env python3
"""
Amazon Lex V2 Automated Chatbot Designer validation and serialization
"""

import json
import re
from datetime import datetime
from collections import OrderedDict
from typing import Dict, List, Tuple, Any

# Artifact detection patterns
ARTIFACT_PATTERNS = [
    r'provide the text.*replace.*placeholders?',
    r'prompt|replace placeholders?|system message|few-shot|LLM',
    r'please provide.*text.*want.*replace',
    r'I need.*text.*replace.*placeholders?',
    r'^\s*$'  # Empty or whitespace-only lines
]

class LexValidationError(Exception):
    """Lex validation specific error"""
    pass

class LexValidator:
    def __init__(self):
        self.artifact_regex = [re.compile(pattern, re.IGNORECASE) for pattern in ARTIFACT_PATTERNS]
    
    def validate_top_level_order(self, obj: Dict) -> Tuple[bool, str]:
        """Validate top-level keys are in canonical order"""
        required_order = ["Participants", "Version", "ContentMetadata", "CustomerMetadata", "Transcript"]
        actual_keys = list(obj.keys())
        
        # Check if all required keys exist
        missing = set(required_order) - set(actual_keys)
        if missing:
            return False, f"Missing required keys: {missing}"
        
        # Check order of required keys
        required_positions = {key: i for i, key in enumerate(required_order)}
        actual_positions = {key: i for i, key in enumerate(actual_keys) if key in required_positions}
        
        for key in required_order:
            if key in actual_positions:
                expected_pos = required_positions[key]
                actual_pos = actual_positions[key]
                if actual_pos != expected_pos:
                    return False, f"Key '{key}' in wrong position. Expected position {expected_pos}, got {actual_pos}"
        
        return True, "Order valid"
    
    def validate_schema_required_fields(self, obj: Dict) -> Tuple[bool, str]:
        """Validate all required fields exist with correct structure"""
        # Check Participants
        if not isinstance(obj.get("Participants"), list) or not obj["Participants"]:
            return False, "Participants must be non-empty list"
        
        # Check Version
        if obj.get("Version") != "1.1.0":
            return False, f"Version must be '1.1.0', got '{obj.get('Version')}'"
        
        # Check ContentMetadata
        content_meta = obj.get("ContentMetadata", {})
        if not isinstance(content_meta, dict):
            return False, "ContentMetadata must be object"
        if "RedactionTypes" not in content_meta or content_meta["RedactionTypes"] != ["PII"]:
            return False, "ContentMetadata.RedactionTypes must be ['PII']"
        if content_meta.get("Output") not in ["Raw", "Redacted"]:
            return False, "ContentMetadata.Output must be 'Raw' or 'Redacted'"
        
        # Check CustomerMetadata
        customer_meta = obj.get("CustomerMetadata", {})
        if not isinstance(customer_meta, dict) or "ContactId" not in customer_meta:
            return False, "CustomerMetadata must contain ContactId"
        
        # Check Transcript
        if not isinstance(obj.get("Transcript"), list) or not obj["Transcript"]:
            return False, "Transcript must be non-empty list"
        
        return True, "Schema valid"
    
    def validate_participants_roles(self, obj: Dict) -> Tuple[bool, str]:
        """Validate participant roles are AGENT or CUSTOMER"""
        participants = obj.get("Participants", [])
        
        for i, participant in enumerate(participants):
            if not isinstance(participant, dict):
                return False, f"Participant {i} must be object"
            
            if "ParticipantId" not in participant or "ParticipantRole" not in participant:
                return False, f"Participant {i} missing ParticipantId or ParticipantRole"
            
            role = participant["ParticipantRole"]
            if role not in ["AGENT", "CUSTOMER"]:
                return False, f"Participant {i} role '{role}' must be 'AGENT' or 'CUSTOMER'"
        
        return True, "Participant roles valid"
    
    def validate_transcript_refs(self, obj: Dict) -> Tuple[bool, str]:
        """Validate transcript references valid participants"""
        participants = obj.get("Participants", [])
        participant_ids = {p["ParticipantId"] for p in participants if isinstance(p, dict) and "ParticipantId" in p}
        
        transcript = obj.get("Transcript", [])
        for i, turn in enumerate(transcript):
            if not isinstance(turn, dict):
                return False, f"Transcript turn {i} must be object"
            
            required_fields = ["ParticipantId", "Id", "Content"]
            for field in required_fields:
                if field not in turn:
                    return False, f"Transcript turn {i} missing {field}"
            
            if turn["ParticipantId"] not in participant_ids:
                return False, f"Transcript turn {i} references unknown ParticipantId '{turn['ParticipantId']}'"
        
        return True, "Transcript references valid"
    
    def validate_unique_ids(self, obj: Dict) -> Tuple[bool, str]:
        """Validate transcript IDs are unique"""
        transcript = obj.get("Transcript", [])
        ids = [turn.get("Id") for turn in transcript if isinstance(turn, dict)]
        
        if len(ids) != len(set(ids)):
            duplicates = [id for id in ids if ids.count(id) > 1]
            return False, f"Duplicate transcript IDs found: {set(duplicates)}"
        
        return True, "Transcript IDs unique"
    
    def validate_filename_date(self, filename: str) -> Tuple[bool, str]:
        """Validate filename contains yyyy-mm-dd date"""
        date_pattern = r'\d{4}-\d{2}-\d{2}'
        if not re.search(date_pattern, filename):
            return False, f"Filename '{filename}' must contain yyyy-mm-dd date"
        return True, "Filename date valid"
    
    def detect_artifacts(self, content: str) -> bool:
        """Detect if content contains generator artifacts"""
        for pattern in self.artifact_regex:
            if pattern.search(content):
                return True
        return False
    
    def remove_artifacts(self, obj: Dict) -> Tuple[Dict, int]:
        """Remove artifact lines from transcript, return (cleaned_obj, removed_count)"""
        transcript = obj.get("Transcript", [])
        cleaned_transcript = []
        removed_count = 0
        
        for turn in transcript:
            if isinstance(turn, dict) and "Content" in turn:
                content = turn["Content"].strip()
                if content and not self.detect_artifacts(content):
                    cleaned_transcript.append(turn)
                else:
                    removed_count += 1
            else:
                cleaned_transcript.append(turn)  # Keep malformed turns for other validation
        
        # Create new object with cleaned transcript
        cleaned_obj = obj.copy()
        cleaned_obj["Transcript"] = cleaned_transcript
        
        return cleaned_obj, removed_count
    
    def run_all_validations(self, obj: Dict, filename: str = None) -> Dict[str, Any]:
        """Run all validations and return structured report"""
        report = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "artifact_count": 0
        }
        
        validations = [
            ("top_level_order", self.validate_top_level_order),
            ("schema_fields", self.validate_schema_required_fields),
            ("participant_roles", self.validate_participants_roles),
            ("transcript_refs", self.validate_transcript_refs),
            ("unique_ids", self.validate_unique_ids)
        ]
        
        for name, validator in validations:
            try:
                valid, message = validator(obj)
                if not valid:
                    report["valid"] = False
                    report["errors"].append(f"{name}: {message}")
            except Exception as e:
                report["valid"] = False
                report["errors"].append(f"{name}: Exception - {e}")
        
        # Filename validation
        if filename:
            try:
                valid, message = self.validate_filename_date(filename)
                if not valid:
                    report["warnings"].append(f"filename: {message}")
            except Exception as e:
                report["warnings"].append(f"filename: Exception - {e}")
        
        # Artifact detection
        transcript = obj.get("Transcript", [])
        for turn in transcript:
            if isinstance(turn, dict) and "Content" in turn:
                if self.detect_artifacts(turn["Content"]):
                    report["artifact_count"] += 1
        
        return report

def serialize_canonical_lex(obj: Dict) -> str:
    """Serialize object in canonical Lex V2 key order"""
    canonical_order = ["Participants", "Version", "ContentMetadata", "CustomerMetadata", "Transcript"]
    
    # Create ordered dict with canonical key order
    ordered_obj = OrderedDict()
    
    # Add keys in canonical order
    for key in canonical_order:
        if key in obj:
            ordered_obj[key] = obj[key]
    
    # Add any remaining keys (shouldn't happen in valid Lex format)
    for key, value in obj.items():
        if key not in ordered_obj:
            ordered_obj[key] = value
    
    return json.dumps(ordered_obj, indent=2, ensure_ascii=True)

def fix_lex_object(obj: Dict, pii_mode: str = "raw") -> Dict:
    """Auto-fix common Lex format issues"""
    fixed_obj = obj.copy()
    
    # Fix Version
    fixed_obj["Version"] = "1.1.0"
    
    # Fix ContentMetadata
    if "ContentMetadata" not in fixed_obj:
        fixed_obj["ContentMetadata"] = {}
    
    fixed_obj["ContentMetadata"]["RedactionTypes"] = ["PII"]
    fixed_obj["ContentMetadata"]["Output"] = "Redacted" if pii_mode == "safe" else "Raw"
    
    # Ensure CustomerMetadata exists
    if "CustomerMetadata" not in fixed_obj:
        fixed_obj["CustomerMetadata"] = {"ContactId": f"auto-{datetime.now().strftime('%Y%m%d-%H%M%S')}"}
    elif "ContactId" not in fixed_obj["CustomerMetadata"]:
        fixed_obj["CustomerMetadata"]["ContactId"] = f"auto-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    return fixed_obj

def generate_lex_filename(contact_id: str = None, date_override: str = None) -> str:
    """Generate Lex-compliant filename with date"""
    if date_override:
        date_str = date_override
    else:
        date_str = datetime.now().strftime("%Y-%m-%d")
    
    if contact_id:
        # Extract UUID-like part from contact_id if present
        clean_id = re.sub(r'[^a-zA-Z0-9-]', '', contact_id)[:8]
        return f"conversation_{date_str}_{clean_id}.json"
    else:
        # Generate new UUID-like suffix
        import uuid
        return f"conversation_{date_str}_{str(uuid.uuid4())[:8]}.json"

# Example usage and testing
if __name__ == "__main__":
    # Test canonical serialization
    test_obj = {
        "Transcript": [{"ParticipantId": "C1", "Id": "T000001", "Content": "Hello"}],
        "Version": "1.1.0",
        "Participants": [{"ParticipantId": "C1", "ParticipantRole": "CUSTOMER"}],
        "CustomerMetadata": {"ContactId": "test-123"},
        "ContentMetadata": {"RedactionTypes": ["PII"], "Output": "Raw"}
    }
    
    validator = LexValidator()
    
    # Test validation
    report = validator.run_all_validations(test_obj, "test_2024-01-15_abc123.json")
    print("Validation Report:", json.dumps(report, indent=2))
    
    # Test serialization
    canonical_json = serialize_canonical_lex(test_obj)
    print("\nCanonical JSON:")
    print(canonical_json)