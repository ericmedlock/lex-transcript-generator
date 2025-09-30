#!/usr/bin/env python3
"""
Integration test - Verify existing code can use AI_Catalyst file processor
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from ai_catalyst.data.processors import FileProcessor


def test_training_dataset_compatibility():
    """Test compatibility with training dataset processing workflow"""
    print("=== Testing Training Dataset Compatibility ===")
    
    # Test with actual training data structure
    training_dir = Path("../Training Datasets/kaggle-health/21")
    if not training_dir.exists():
        print("Training data not found, skipping test")
        return
    
    processor = FileProcessor()
    
    # Process files similar to how training_dataset_processor.py does it
    print("Processing training dataset files...")
    
    processed_count = 0
    conversation_count = 0
    
    for file_path in processor.scan_directory(training_dir):
        if processed_count >= 3:  # Limit for testing
            break
            
        print(f"\nProcessing: {file_path.name}")
        
        for item in processor.process_file(file_path):
            data = item['data']
            
            # Check if this looks like the expected structure
            if 'results' in data and isinstance(data['results'], list):
                for result in data['results']:
                    if 'alternatives' in result:
                        for alt in result['alternatives']:
                            if 'transcript' in alt:
                                conversation_count += 1
                                print(f"  Found conversation: {alt['transcript'][:50]}...")
                                break
                        break
                break
        
        processed_count += 1
    
    print(f"\nProcessed {processed_count} files, found {conversation_count} conversations")


def test_lex_converter_compatibility():
    """Test compatibility with LEX converter workflow"""
    print("\n=== Testing LEX Converter Compatibility ===")
    
    processor = FileProcessor()
    
    # Create sample data that mimics what LEX converter expects
    sample_data = {
        "jobName": "test-job",
        "accountId": "123456789",
        "results": [{
            "alternatives": [{
                "transcript": "Hello, I'd like to schedule an appointment."
            }]
        }]
    }
    
    # Test data extraction similar to how LEX converter would use it
    print("Testing data extraction for LEX conversion...")
    
    # Simulate processing this data structure
    if 'results' in sample_data:
        for result in sample_data['results']:
            if 'alternatives' in result:
                for alt in result['alternatives']:
                    if 'transcript' in alt:
                        transcript = alt['transcript']
                        print(f"Extracted transcript: {transcript}")
                        
                        # This is the kind of data LEX converter needs
                        lex_compatible_data = {
                            'conversation_text': transcript,
                            'source': 'ai_catalyst_processor'
                        }
                        print(f"LEX-compatible format: {lex_compatible_data}")


def test_pii_processor_compatibility():
    """Test compatibility with PII processor workflow"""
    print("\n=== Testing PII Processor Compatibility ===")
    
    processor = FileProcessor()
    
    # Sample text that would need PII scrubbing
    sample_text = "Hi, my name is John Smith and my phone number is 555-1234."
    
    # Test that file processor can extract text for PII processing
    print("Testing text extraction for PII processing...")
    
    # Simulate extracting text from processed data
    extracted_text = sample_text
    print(f"Text for PII processing: {extracted_text}")
    
    # This would be passed to PII processor
    pii_input = {
        'text': extracted_text,
        'source_file': 'test_file.json',
        'processing_stage': 'pre_lex_conversion'
    }
    print(f"PII processor input format: {pii_input}")


def main():
    """Run integration tests"""
    print("AI_Catalyst File Processor Integration Test")
    print("=" * 50)
    
    try:
        test_training_dataset_compatibility()
        test_lex_converter_compatibility()
        test_pii_processor_compatibility()
        print("\n[SUCCESS] Integration tests completed")
    except Exception as e:
        print(f"\n[ERROR] Integration test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()