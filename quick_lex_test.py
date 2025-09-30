#!/usr/bin/env python3
"""
Quick Lex Quality Test - Test on just 3-5 files first
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple

def quick_test_files(directory: Path, max_files: int = 3):
    """Test analysis on just a few files"""
    files = list(directory.glob("*.json"))[:max_files]
    print(f"\nTesting {len(files)} files from {directory}")
    
    for file_path in files:
        print(f"\n--- {file_path.name} ---")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Quick format check
            required_fields = ['Version', 'Participants', 'Transcript', 'ContentMetadata']
            missing = [f for f in required_fields if f not in data]
            if missing:
                print(f"[FAIL] Missing fields: {missing}")
            else:
                print("[PASS] Has required fields")
            
            # Version check
            version = data.get('Version', 'missing')
            print(f"Version: {version}")
            
            # Participant count
            participants = data.get('Participants', [])
            print(f"Participants: {len(participants)}")
            for p in participants:
                print(f"  - {p.get('ParticipantId', 'no-id')}: {p.get('ParticipantRole', 'no-role')}")
            
            # Turn count and sample
            transcript = data.get('Transcript', [])
            print(f"Turns: {len(transcript)}")
            
            if transcript:
                # Show first turn
                first_turn = transcript[0]
                content = first_turn.get('Content', '')[:100] + "..." if len(first_turn.get('Content', '')) > 100 else first_turn.get('Content', '')
                print(f"First turn: {first_turn.get('ParticipantId', 'no-id')} - {content}")
                
                # Quick PII check on first few turns
                pii_patterns = {
                    'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
                    'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                    'ssn': r'\b\d{3}-\d{2}-\d{4}\b'
                }
                
                pii_found = []
                for turn in transcript[:3]:  # Check first 3 turns
                    content = turn.get('Content', '')
                    for pii_type, pattern in pii_patterns.items():
                        if re.search(pattern, content):
                            pii_found.append(pii_type)
                
                if pii_found:
                    print(f"[WARN] PII detected: {set(pii_found)}")
                else:
                    print("[PASS] No obvious PII in first 3 turns")
            
        except Exception as e:
            print(f"[ERROR] {e}")

def main():
    print("Quick Lex Quality Test")
    print("="*50)
    
    # Test health-calls-output
    health_dir = Path("Training Datasets/health-calls-output")
    if health_dir.exists():
        quick_test_files(health_dir, 3)
    else:
        print(f"[ERROR] Directory not found: {health_dir}")
    
    # Test lex_export  
    lex_dir = Path("lex_export/2025-09-29")
    if lex_dir.exists():
        quick_test_files(lex_dir, 3)
    else:
        print(f"[ERROR] Directory not found: {lex_dir}")

if __name__ == "__main__":
    main()