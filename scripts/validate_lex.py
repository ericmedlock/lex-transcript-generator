#!/usr/bin/env python3
"""
LEX JSON Validator - Validate exported LEX files
"""

import json
import re
from pathlib import Path
import argparse

def validate_lex_file(file_path):
    """Validate a single LEX JSON file"""
    errors = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return [f"Invalid JSON: {e}"]
    except Exception as e:
        return [f"Cannot read file: {e}"]
    
    # Check required top-level fields
    required_fields = ["Participants", "Version", "ContentMetadata", "CustomerMetadata", "Transcript"]
    for field in required_fields:
        if field not in data:
            errors.append(f"Missing required field: {field}")
    
    # Check version
    if data.get("Version") != "1.1.0":
        errors.append(f"Invalid version: {data.get('Version')}, expected 1.1.0")
    
    # Check participants
    participants = data.get("Participants", [])
    if not participants:
        errors.append("No participants defined")
    
    participant_ids = set()
    for i, participant in enumerate(participants):
        if "ParticipantId" not in participant:
            errors.append(f"Participant {i} missing ParticipantId")
        else:
            participant_ids.add(participant["ParticipantId"])
        
        if "ParticipantRole" not in participant:
            errors.append(f"Participant {i} missing ParticipantRole")
        elif participant["ParticipantRole"] not in ["AGENT", "CUSTOMER"]:
            errors.append(f"Invalid ParticipantRole: {participant['ParticipantRole']}")
    
    # Check ContentMetadata
    content_meta = data.get("ContentMetadata", {})
    if "Output" not in content_meta:
        errors.append("Missing ContentMetadata.Output")
    elif content_meta["Output"] not in ["Raw", "Redacted"]:
        errors.append(f"Invalid ContentMetadata.Output: {content_meta['Output']}")
    
    # Check transcript
    transcript = data.get("Transcript", [])
    if not transcript:
        errors.append("Empty transcript")
    
    for i, turn in enumerate(transcript):
        required_turn_fields = ["ParticipantId", "Id", "Content"]
        for field in required_turn_fields:
            if field not in turn:
                errors.append(f"Turn {i} missing {field}")
        
        # Check participant ID reference
        if turn.get("ParticipantId") not in participant_ids:
            errors.append(f"Turn {i} references unknown ParticipantId: {turn.get('ParticipantId')}")
    
    return errors

def validate_filename(file_path):
    """Validate filename contains date in yyyy-mm-dd format"""
    filename = Path(file_path).name
    date_pattern = r'\d{4}-\d{2}-\d{2}'
    
    if not re.search(date_pattern, filename):
        return [f"Filename missing yyyy-mm-dd date: {filename}"]
    
    return []

def main():
    parser = argparse.ArgumentParser(description="Validate LEX JSON files")
    parser.add_argument("path", help="File or directory to validate")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed output")
    
    args = parser.parse_args()
    
    path = Path(args.path)
    
    if path.is_file():
        files = [path]
    elif path.is_dir():
        files = list(path.rglob("*.json"))
    else:
        print(f"❌ Path not found: {path}")
        return 1
    
    if not files:
        print("❌ No JSON files found")
        return 1
    
    total_files = len(files)
    passed_files = 0
    total_errors = 0
    
    print(f"Validating {total_files} files...")
    
    for file_path in files:
        filename_errors = validate_filename(file_path)
        content_errors = validate_lex_file(file_path)
        
        all_errors = filename_errors + content_errors
        
        if all_errors:
            total_errors += len(all_errors)
            if args.verbose:
                print(f"\n❌ {file_path.name}:")
                for error in all_errors:
                    print(f"  - {error}")
            else:
                print(f"❌ {file_path.name} ({len(all_errors)} errors)")
        else:
            passed_files += 1
            if args.verbose:
                print(f"✅ {file_path.name}")
    
    print(f"\nValidation Summary:")
    print(f"  Files processed: {total_files}")
    print(f"  Passed: {passed_files}")
    print(f"  Failed: {total_files - passed_files}")
    print(f"  Total errors: {total_errors}")
    
    if passed_files == total_files:
        print("🎉 All files passed validation!")
        return 0
    else:
        print("❌ Some files failed validation")
        return 1

if __name__ == "__main__":
    exit(main())