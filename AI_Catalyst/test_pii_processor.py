#!/usr/bin/env python3
"""
Test script for AI_Catalyst PII Processor
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from ai_catalyst.data.pii import PIIProcessor, PIIEngine


def test_regex_pii_processing():
    """Test regex-based PII processing"""
    print("=== Testing Regex PII Processing ===")
    
    # Initialize processor with regex strategy
    processor = PIIProcessor(config={
        'default_strategy': 'regex',
        'placeholder_style': 'angle'
    })
    
    # Test text with various PII types
    test_text = """
    Hi, my name is John Smith and I live at 123 Main Street, New York.
    You can reach me at john.smith@email.com or call 555-123-4567.
    My appointment is on 03/15/2024 and my insurance ID is ABC123456.
    My social security number is 123-45-6789.
    """
    
    print("Original text:")
    print(test_text.strip())
    
    # Detect PII
    pii_counts = processor.detect_pii(test_text)
    print(f"\nDetected PII: {pii_counts}")
    
    # Scrub PII
    scrubbed_text = processor.scrub_text(test_text)
    print(f"\nScrubbed text:")
    print(scrubbed_text.strip())


def test_llm_pii_processing():
    """Test LLM-based PII processing if available"""
    print("\n=== Testing LLM PII Processing ===")
    
    # Initialize processor with LLM strategy
    processor = PIIProcessor(config={
        'default_strategy': 'llm',
        'llm_endpoint': 'http://127.0.0.1:1234/v1/chat/completions',
        'llm_timeout': 10,
        'fallback_to_regex': True
    })
    
    test_text = "Hello, I'm Jane Doe and my phone number is 555-987-6543."
    
    print(f"Original text: {test_text}")
    
    try:
        scrubbed_text = processor.scrub_text(test_text, strategy='llm')
        print(f"LLM scrubbed text: {scrubbed_text}")
    except Exception as e:
        print(f"LLM processing failed (expected if no LLM running): {e}")


def test_batch_processing():
    """Test batch PII processing"""
    print("\n=== Testing Batch Processing ===")
    
    processor = PIIProcessor(config={'default_strategy': 'regex'})
    
    test_texts = [
        "My name is Alice Johnson, phone: 555-111-2222",
        "Contact Bob Wilson at bob@company.com",
        "Sarah's address is 456 Oak Avenue, Chicago"
    ]
    
    print("Original texts:")
    for i, text in enumerate(test_texts, 1):
        print(f"  {i}: {text}")
    
    scrubbed_texts = processor.batch_scrub_texts(test_texts)
    
    print("\nScrubbed texts:")
    for i, text in enumerate(scrubbed_texts, 1):
        print(f"  {i}: {text}")


def test_pii_engine():
    """Test low-level PII engine"""
    print("\n=== Testing PII Engine ===")
    
    test_text = "Call me at 555-123-4567 or email test@example.com"
    
    # Test pattern detection
    patterns = {
        'PHONE': r'\\b\\d{3}-\\d{3}-\\d{4}\\b',
        'EMAIL': r'\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}\\b'
    }
    
    matches = PIIEngine.detect_pii_patterns(test_text, patterns)
    print(f"Pattern matches: {matches}")
    
    # Test pattern replacement
    scrubbed = PIIEngine.replace_pii_patterns(test_text, patterns, "<{}>")
    print(f"Pattern replacement: {scrubbed}")


def test_configuration_options():
    """Test different configuration options"""
    print("\n=== Testing Configuration Options ===")
    
    test_text = "Contact John at 555-123-4567"
    
    # Test different placeholder styles
    configs = [
        {'placeholder_style': 'angle'},
        {'placeholder_style': 'bracket'},
    ]
    
    for config in configs:
        processor = PIIProcessor(config=config)
        result = processor.scrub_text(test_text)
        print(f"Style '{config['placeholder_style']}': {result}")


def main():
    """Run tests"""
    print("AI_Catalyst PII Processor Test")
    print("=" * 40)
    
    try:
        test_regex_pii_processing()
        test_llm_pii_processing()
        test_batch_processing()
        test_pii_engine()
        test_configuration_options()
        print("\n[SUCCESS] PII processor tests completed")
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()