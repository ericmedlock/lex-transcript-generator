#!/usr/bin/env python3
"""
AWS Transcribe to Lex V2 Converter - Pipeline 2
Converts AWS Transcribe format to Amazon Lex V2 Automated Chatbot Designer format
"""

import json
import argparse
import sys
import os
from pathlib import Path
from datetime import datetime
import uuid

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.lex_validator import serialize_canonical_lex, generate_lex_filename

try:
    from pii_scrubber.engine import scrub_text
    from pii_scrubber.llm_client import LLMUnavailableError
    import yaml
    PII_AVAILABLE = True
except ImportError:
    PII_AVAILABLE = False
    def scrub_text(text, mode, strategy, config): return text
    class LLMUnavailableError(Exception): pass

def load_pii_config():
    """Load PII scrubbing configuration"""
    try:
        with open("pii_scrubber/config.yaml", 'r') as f:
            return yaml.safe_load(f)
    except:
        return {
            'default_mode': 'safe',
            'default_strategy': 'llm',
            'llm': {'endpoint': 'http://127.0.0.1:1234/v1/chat/completions'},
            'scrub': {'placeholder_style': 'angle'}
        }

def convert_transcribe_to_lex(transcribe_data, pii_mode="safe", pii_strategy="llm", pii_config=None):
    """Convert AWS Transcribe format to Lex V2 format"""
    
    # Extract speaker segments and build transcript turns
    segments = transcribe_data.get("results", {}).get("speaker_labels", {}).get("segments", [])
    transcript_text = transcribe_data.get("results", {}).get("transcripts", [{}])[0].get("transcript", "")
    
    # Create participants from unique speakers
    speakers = set()
    for segment in segments:
        speakers.add(segment.get("speaker_label", "spk_0"))
    
    participants = []
    for i, speaker in enumerate(sorted(speakers)):
        role = "AGENT" if i == 0 else "CUSTOMER"
        participants.append({
            "ParticipantId": speaker,
            "ParticipantRole": role
        })
    
    # Build transcript turns from segments
    transcript_turns = []
    for i, segment in enumerate(segments):
        speaker_id = segment.get("speaker_label", "spk_0")
        
        # Extract text for this segment from items
        segment_text = ""
        items = transcribe_data.get("results", {}).get("items", [])
        
        # Find audio_segments that match this segment
        audio_segments = transcribe_data.get("results", {}).get("audio_segments", [])
        for audio_seg in audio_segments:
            if (audio_seg.get("speaker_label") == speaker_id and 
                audio_seg.get("start_time") == segment.get("start_time")):
                segment_text = audio_seg.get("transcript", "")
                break
        
        # Fallback: use full transcript if no segment text found
        if not segment_text:
            segment_text = transcript_text
        
        # Apply PII scrubbing
        if pii_mode == "safe" and PII_AVAILABLE:
            try:
                config_with_fallback = pii_config.copy() if pii_config else {}
                config_with_fallback['fallback_to_regex'] = pii_strategy != "llm"
                segment_text = scrub_text(segment_text, pii_mode, pii_strategy, config_with_fallback)
            except LLMUnavailableError:
                pass  # Keep original text if LLM fails
        
        transcript_turns.append({
            "ParticipantId": speaker_id,
            "Id": f"T{i+1:06d}",
            "Content": segment_text
        })
    
    # If no segments, create single turn from full transcript
    if not transcript_turns and transcript_text:
        # Apply PII scrubbing to full text
        content = transcript_text
        if pii_mode == "safe" and PII_AVAILABLE:
            try:
                config_with_fallback = pii_config.copy() if pii_config else {}
                config_with_fallback['fallback_to_regex'] = pii_strategy != "llm"
                content = scrub_text(content, pii_mode, pii_strategy, config_with_fallback)
            except LLMUnavailableError:
                pass
        
        transcript_turns.append({
            "ParticipantId": "spk_0",
            "Id": "T000001", 
            "Content": content
        })
        
        # Ensure we have a participant
        if not participants:
            participants.append({
                "ParticipantId": "spk_0",
                "ParticipantRole": "CUSTOMER"
            })
    
    # Build Lex V2 object
    lex_object = {
        "Participants": participants,
        "Version": "1.1.0",
        "ContentMetadata": {
            "RedactionTypes": ["PII"],
            "Output": "Redacted" if pii_mode == "safe" else "Raw"
        },
        "CustomerMetadata": {
            "ContactId": f"auto-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        },
        "Transcript": transcript_turns
    }
    
    return lex_object

def process_file(input_path, output_dir, pii_mode, pii_strategy, pii_config):
    """Process single AWS Transcribe file to Lex V2"""
    try:
        # Load AWS Transcribe data
        with open(input_path, 'r', encoding='utf-8') as f:
            transcribe_data = json.load(f)
        
        # Convert to Lex V2
        lex_data = convert_transcribe_to_lex(transcribe_data, pii_mode, pii_strategy, pii_config)
        
        # Generate output filename with date from input filename
        # Extract date from input filename if present, otherwise use today
        import re
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', input_path.name)
        if date_match:
            file_date = date_match.group(1)
        else:
            file_date = datetime.now().strftime("%Y-%m-%d")
        
        # Extract unique ID from filename (after 'call')
        id_match = re.search(r'call([a-f0-9-]+)', input_path.name)
        if id_match:
            unique_id = id_match.group(1)[:8]  # First 8 chars of UUID
        else:
            unique_id = str(uuid.uuid4())[:8]  # Fallback to random UUID
        
        output_filename = f"conversation_{file_date}_{unique_id}.json"
        output_path = output_dir / output_filename
        
        # Write Lex V2 file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(serialize_canonical_lex(lex_data))
        
        print(f"+ {input_path.name} -> {output_filename}")
        return True
        
    except Exception as e:
        print(f"- {input_path.name}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Convert AWS Transcribe to Lex V2 format")
    parser.add_argument("input_dir", help="Input directory with AWS Transcribe JSON files")
    parser.add_argument("output_dir", help="Output directory for Lex V2 files")
    parser.add_argument("--mode", choices=["safe", "raw"], default="safe", help="PII scrubbing mode")
    parser.add_argument("--pii-strategy", choices=["llm", "regex", "off"], default="llm", help="PII strategy")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    
    args = parser.parse_args()
    
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    
    if not input_dir.exists():
        print(f"ERROR: Input directory {input_dir} does not exist")
        return 1
    
    # Find all JSON files recursively
    json_files = list(input_dir.glob("**/*.json"))
    if not json_files:
        print("No JSON files found")
        return 0
    
    print(f"Converting {len(json_files)} AWS Transcribe files to Lex V2 format")
    print(f"PII mode: {args.mode}, strategy: {args.pii_strategy}")
    
    if not args.dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load PII config
    pii_config = load_pii_config() if PII_AVAILABLE else {}
    
    # Process files
    processed = 0
    failed = 0
    
    for json_file in json_files:
        if args.dry_run:
            print(f"[DRY RUN] Would convert: {json_file.name}")
            processed += 1
        else:
            if process_file(json_file, output_dir, args.mode, args.pii_strategy, pii_config):
                processed += 1
            else:
                failed += 1
    
    print(f"\nConversion complete:")
    print(f"  Processed: {processed}")
    print(f"  Failed: {failed}")
    print(f"  Output: {output_dir}")
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    exit(main())