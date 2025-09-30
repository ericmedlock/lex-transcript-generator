#!/usr/bin/env python3
"""
Test script for AI_Catalyst File Processor
"""

import sys
import os
import json
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from ai_catalyst.data.processors import FileProcessor


def create_test_files():
    """Create test files for processing"""
    test_dir = Path(tempfile.mkdtemp())
    
    # JSON file with single conversation
    json_single = test_dir / "single.json"
    with open(json_single, 'w') as f:
        json.dump({"conversation": "Hello, how are you?", "type": "greeting"}, f)
    
    # JSON file with multiple conversations
    json_multi = test_dir / "multi.json"
    with open(json_multi, 'w') as f:
        json.dump([
            {"conversation": "Hello", "type": "greeting"},
            {"conversation": "Goodbye", "type": "farewell"}
        ], f)
    
    # JSONL file
    jsonl_file = test_dir / "data.jsonl"
    with open(jsonl_file, 'w') as f:
        f.write('{"text": "Line 1", "id": 1}\n')
        f.write('{"text": "Line 2", "id": 2}\n')
    
    # CSV file
    csv_file = test_dir / "data.csv"
    with open(csv_file, 'w') as f:
        f.write("name,age,city\n")
        f.write("John,25,NYC\n")
        f.write("Jane,30,LA\n")
    
    # TXT file
    txt_file = test_dir / "data.txt"
    with open(txt_file, 'w') as f:
        f.write("First paragraph of text.\n\nSecond paragraph of text.")
    
    return test_dir


def test_file_processing():
    """Test file processing functionality"""
    print("=== Testing File Processing ===")
    
    # Create test files
    test_dir = create_test_files()
    print(f"Created test files in: {test_dir}")
    
    # Initialize processor
    processor = FileProcessor()
    
    # Test directory scanning
    print("\nScanning directory...")
    files = list(processor.scan_directory(test_dir))
    print(f"Found {len(files)} supported files:")
    for file_path in files:
        print(f"  {file_path.name}")
    
    # Test directory stats
    print("\nDirectory statistics:")
    stats = processor.get_directory_stats(test_dir)
    print(f"  Total files: {stats['total_files']}")
    print(f"  By extension: {stats['by_extension']}")
    print(f"  Total size: {stats['total_size']} bytes")
    
    # Test processing each file type
    print("\nProcessing files:")
    for file_path in files:
        print(f"\n--- Processing {file_path.name} ---")
        items = list(processor.process_file(file_path))
        print(f"Extracted {len(items)} items:")
        
        for i, item in enumerate(items[:2]):  # Show first 2 items
            print(f"  Item {i}: {str(item['data'])[:50]}...")
            print(f"    Source: {Path(item['source_file']).name}")
            print(f"    Index: {item['index']}")
    
    # Test processing entire directory
    print(f"\n--- Processing entire directory ---")
    all_items = list(processor.process_directory(test_dir))
    print(f"Total items from all files: {len(all_items)}")
    
    # Cleanup
    import shutil
    shutil.rmtree(test_dir)
    print(f"\nCleaned up test directory")


def test_integration_with_existing_data():
    """Test with existing project data"""
    print("\n=== Testing with Existing Data ===")
    
    # Test with Training Datasets if available
    training_dir = Path("../Training Datasets/kaggle-health/21")
    if training_dir.exists():
        print(f"Testing with existing data: {training_dir}")
        
        processor = FileProcessor()
        
        # Get stats
        stats = processor.get_directory_stats(training_dir)
        print(f"Found {stats['total_files']} files")
        print(f"Extensions: {stats['by_extension']}")
        
        # Process a few files
        files = list(processor.scan_directory(training_dir))
        if files:
            print(f"\nProcessing first file: {files[0].name}")
            items = list(processor.process_file(files[0]))
            if items:
                print(f"Sample data keys: {list(items[0]['data'].keys())}")
                print(f"Metadata: {items[0]['metadata']['filename']}")
    else:
        print("Training data directory not found, skipping integration test")


def main():
    """Run tests"""
    print("AI_Catalyst File Processor Test")
    print("=" * 40)
    
    try:
        test_file_processing()
        test_integration_with_existing_data()
        print("\n[SUCCESS] File processor tests completed")
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()