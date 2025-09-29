#!/usr/bin/env python3
"""Test Lex V2 compliance implementation"""

import json
import tempfile
from pathlib import Path
from src.core.lex_validator import LexValidator, serialize_canonical_lex, fix_lex_object

def test_validation_and_serialization():
    """Test validation and canonical serialization"""
    print("Testing Lex V2 validation and serialization...")
    
    # Test data with wrong order and artifacts
    test_conversation = {
        "Transcript": [
            {"ParticipantId": "C1", "Id": "T000001", "Content": "Hi, I'd like to make an appointment"},
            {"ParticipantId": "A1", "Id": "T000002", "Content": "Please provide the text you want me to replace the placeholders in."},  # ARTIFACT
            {"ParticipantId": "A1", "Id": "T000003", "Content": "Sure, what type of appointment?"},
            {"ParticipantId": "C1", "Id": "T000004", "Content": "Annual checkup please"}
        ],
        "Version": "1.0.0",  # WRONG VERSION
        "Participants": [
            {"ParticipantId": "C1", "ParticipantRole": "CUSTOMER"},
            {"ParticipantId": "A1", "ParticipantRole": "AGENT"}
        ],
        "CustomerMetadata": {"ContactId": "test-123"},
        "ContentMetadata": {"RedactionTypes": ["PII"], "Output": "Raw"}
    }
    
    validator = LexValidator()
    
    # Test validation (should fail)
    report = validator.run_all_validations(test_conversation, "test_2024-01-15.json")
    print(f"Initial validation - Valid: {report['valid']}")
    print(f"Errors: {report['errors']}")
    print(f"Artifacts found: {report['artifact_count']}")
    
    # Test auto-fix
    fixed_conversation = fix_lex_object(test_conversation, "raw")
    print(f"Fixed version: {fixed_conversation['Version']}")
    
    # Test artifact removal
    cleaned_conversation, removed_count = validator.remove_artifacts(fixed_conversation)
    print(f"Artifacts removed: {removed_count}")
    print(f"Transcript length after cleaning: {len(cleaned_conversation['Transcript'])}")
    
    # Test final validation (need to re-run validation after cleaning)
    final_report = validator.run_all_validations(cleaned_conversation, "test_2024-01-15.json")
    print(f"Final validation - Valid: {final_report['valid']}")
    if not final_report['valid']:
        print(f"Remaining errors: {final_report['errors']}")
        # Try one more fix
        cleaned_conversation = fix_lex_object(cleaned_conversation, "raw")
        final_report = validator.run_all_validations(cleaned_conversation, "test_2024-01-15.json")
        print(f"After second fix - Valid: {final_report['valid']}")
    
    # Test canonical serialization
    canonical_json = serialize_canonical_lex(cleaned_conversation)
    print("\\nCanonical JSON (first 200 chars):")
    print(canonical_json[:200] + "...")
    
    # Verify key order in serialized output
    parsed = json.loads(canonical_json)
    keys = list(parsed.keys())
    expected_order = ["Participants", "Version", "ContentMetadata", "CustomerMetadata", "Transcript"]
    key_order_correct = keys == expected_order
    print(f"\\nKey order correct: {key_order_correct}")
    print(f"Expected: {expected_order}")
    print(f"Actual:   {keys}")
    
    # Test validation on serialized/parsed object (should pass)
    serialized_report = validator.run_all_validations(parsed, "test_2024-01-15.json")
    print(f"Serialized object validation - Valid: {serialized_report['valid']}")
    
    return serialized_report['valid'] and key_order_correct

def test_filename_generation():
    """Test filename generation"""
    from src.core.lex_validator import generate_lex_filename
    
    print("\\nTesting filename generation...")
    
    # Test with contact ID
    filename1 = generate_lex_filename("contact-abc123", "2024-01-15")
    print(f"With contact ID: {filename1}")
    
    # Test without contact ID
    filename2 = generate_lex_filename()
    print(f"Auto-generated: {filename2}")
    
    # Test filename validation
    validator = LexValidator()
    valid1, msg1 = validator.validate_filename_date(filename1)
    valid2, msg2 = validator.validate_filename_date(filename2)
    
    print(f"Filename 1 valid: {valid1}")
    print(f"Filename 2 valid: {valid2}")
    
    return valid1 and valid2

if __name__ == "__main__":
    print("=" * 60)
    print("LEX V2 COMPLIANCE TEST")
    print("=" * 60)
    
    try:
        # Test validation and serialization
        validation_passed = test_validation_and_serialization()
        
        # Test filename generation
        filename_passed = test_filename_generation()
        
        print("\\n" + "=" * 60)
        print("TEST RESULTS")
        print("=" * 60)
        print(f"Validation & Serialization: {'PASS' if validation_passed else 'FAIL'}")
        print(f"Filename Generation:        {'PASS' if filename_passed else 'FAIL'}")
        
        if validation_passed and filename_passed:
            print("\\n+ All tests PASSED - Lex V2 compliance ready!")
            exit(0)
        else:
            print("\\n- Some tests FAILED")
            exit(1)
            
    except Exception as e:
        print(f"\\nTEST ERROR: {e}")
        exit(1)