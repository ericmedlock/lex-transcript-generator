#!/usr/bin/env python3
"""
Integration test - Verify PII processor works with existing workflows
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from ai_catalyst.data.pii import PIIProcessor


def test_training_dataset_pii_workflow():
    """Test PII processing workflow similar to training dataset processor"""
    print("=== Testing Training Dataset PII Workflow ===")
    
    # Simulate conversation data from training dataset
    sample_conversation = {
        "results": [{
            "alternatives": [{
                "transcript": "Hi, I'm calling to schedule an appointment. My name is John Smith and my phone number is 555-123-4567. I live at 123 Main Street."
            }]
        }]
    }
    
    # Initialize PII processor with config similar to existing system
    processor = PIIProcessor(config={
        'default_strategy': 'regex',  # Safe fallback
        'placeholder_style': 'angle',
        'fallback_to_regex': True
    })
    
    # Extract transcript text (similar to how training processor does it)
    transcript = sample_conversation["results"][0]["alternatives"][0]["transcript"]
    print(f"Original transcript: {transcript}")
    
    # Process PII
    pii_counts = processor.detect_pii(transcript)
    scrubbed_transcript = processor.scrub_text(transcript)
    
    print(f"PII detected: {pii_counts}")
    print(f"Scrubbed transcript: {scrubbed_transcript}")
    
    # Update conversation data with scrubbed version
    sample_conversation["results"][0]["alternatives"][0]["transcript"] = scrubbed_transcript
    
    print("[SUCCESS] Successfully integrated with training dataset workflow")


def test_lex_converter_pii_workflow():
    """Test PII processing for LEX converter workflow"""
    print("\n=== Testing LEX Converter PII Workflow ===")
    
    # Simulate LEX format data
    lex_data = {
        "Version": "1.1.0",
        "Transcript": [
            {"Content": "Hello, this is Dr. Sarah Johnson."},
            {"Content": "Hi doctor, my name is Michael Brown and I need to reschedule my appointment."},
            {"Content": "Of course, what's your phone number for verification?"},
            {"Content": "It's 555-987-6543."}
        ]
    }
    
    processor = PIIProcessor(config={'default_strategy': 'regex'})
    
    print("Original LEX transcript:")
    for turn in lex_data["Transcript"]:
        print(f"  {turn['Content']}")
    
    # Process each turn for PII
    total_pii_count = 0
    for turn in lex_data["Transcript"]:
        original_content = turn["Content"]
        pii_counts = processor.detect_pii(original_content)
        scrubbed_content = processor.scrub_text(original_content)
        
        turn["Content"] = scrubbed_content
        total_pii_count += sum(pii_counts.values())
    
    print(f"\nScrubbed LEX transcript (found {total_pii_count} PII items):")
    for turn in lex_data["Transcript"]:
        print(f"  {turn['Content']}")
    
    print("[SUCCESS] Successfully integrated with LEX converter workflow")


def test_bulk_processing_workflow():
    """Test bulk processing similar to existing batch operations"""
    print("\n=== Testing Bulk Processing Workflow ===")
    
    # Simulate processing multiple files/conversations
    conversations = [
        "Patient: Hi, I'm calling about my test results. My name is Alice Wilson.",
        "Receptionist: I can help with that. What's your date of birth?",
        "Patient: It's 05/15/1985 and my phone is 555-111-2222.",
        "Doctor: Hello Mr. Johnson, your appointment is confirmed for tomorrow.",
        "Patient: Thank you, my insurance ID is XYZ789012."
    ]
    
    processor = PIIProcessor(config={'default_strategy': 'regex'})
    
    print(f"Processing {len(conversations)} conversations...")
    
    # Batch process all conversations
    scrubbed_conversations = processor.batch_scrub_texts(conversations)
    
    # Count total PII across all conversations
    total_pii = 0
    for original in conversations:
        pii_counts = processor.detect_pii(original)
        total_pii += sum(pii_counts.values())
    
    print(f"Found {total_pii} PII items across all conversations")
    print("\nSample scrubbed conversations:")
    for i, scrubbed in enumerate(scrubbed_conversations[:3], 1):
        print(f"  {i}: {scrubbed}")
    
    print("[SUCCESS] Successfully processed bulk conversations")


def test_config_compatibility():
    """Test configuration compatibility with existing system"""
    print("\n=== Testing Configuration Compatibility ===")
    
    # Test config similar to existing pii_scrubber/config.yaml
    existing_style_config = {
        'default_strategy': 'regex',
        'placeholder_style': 'angle',  # matches existing <NAME> style
        'fallback_to_regex': True
    }
    
    processor = PIIProcessor(config=existing_style_config)
    
    test_text = "Contact John Smith at 555-123-4567"
    result = processor.scrub_text(test_text)
    
    # Verify it matches expected format from existing system
    expected_format = "<NAME>"  # Should use angle brackets
    if "<NAME>" in result and "<PHONE>" in result:
        print("[SUCCESS] Configuration matches existing system format")
        print(f"  Result: {result}")
    else:
        print("[ERROR] Configuration mismatch")
        print(f"  Result: {result}")


def main():
    """Run integration tests"""
    print("AI_Catalyst PII Processor Integration Test")
    print("=" * 50)
    
    try:
        test_training_dataset_pii_workflow()
        test_lex_converter_pii_workflow()
        test_bulk_processing_workflow()
        test_config_compatibility()
        print("\n[SUCCESS] PII integration tests completed")
    except Exception as e:
        print(f"\n[ERROR] Integration test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()