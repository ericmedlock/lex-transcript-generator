#!/usr/bin/env python3
"""
LEX Exporter - Export conversations to Amazon LEX Automated Chatbot Designer format
"""

import json
import os
import psycopg2
import argparse
import yaml
import logging
from datetime import datetime, date
from pathlib import Path
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import Lex validator
from src.core.lex_validator import (
    LexValidator, serialize_canonical_lex, fix_lex_object, 
    generate_lex_filename, LexValidationError
)

try:
    from pii_scrubber.engine import scrub_text, detect_pii_regex
    from pii_scrubber.llm_client import LLMUnavailableError
    PII_AVAILABLE = True
except ImportError as e:
    PII_AVAILABLE = False
    def scrub_text(text, mode, strategy, config): return text
    def detect_pii_regex(text): return {}
    class LLMUnavailableError(Exception): pass

def load_db_config():
    """Load database configuration"""
    config_paths = [
        "config/orchestrator_config.json",
        "config/node_config.json"
    ]
    
    for path in config_paths:
        if Path(path).exists():
            with open(path, 'r') as f:
                config = json.load(f)
                if "db_config" in config:
                    return config["db_config"]
                # Check if it's a per-hostname config
                for hostname_config in config.values():
                    if isinstance(hostname_config, dict) and "db_config" in hostname_config:
                        return hostname_config["db_config"]
    
    # Default config
    return {
        "host": "EPM_DELL",
        "port": 5432,
        "database": "calllab",
        "user": "postgres",
        "password": "pass"
    }

def show_data_menu():
    """Display ASCII menu for data selection"""
    print("\n" + "="*50)
    print("         LEX EXPORT DATA SELECTION")
    print("="*50)
    print("1. ALL data")
    print("2. Just the last run")
    print("3. Today")
    print("4. This week")
    print("="*50)
    
    while True:
        try:
            choice = input("Select option (1-4): ").strip()
            if choice in ['1', '2', '3', '4']:
                return int(choice)
            print("Invalid choice. Please enter 1, 2, 3, or 4.")
        except KeyboardInterrupt:
            print("\n\nCancelled by user.")
            return None

def get_conversations(db_config, quality_threshold=None, limit=None, data_filter=None):
    """Fetch conversations from database with filtering options"""
    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()
    
    query = """
        SELECT id, content, quality_score, created_at, model_name
        FROM conversations 
        WHERE content IS NOT NULL
    """
    params = []
    
    # Add data filter
    if data_filter == 2:  # Last run
        cur.execute("SELECT MAX(run_id) FROM conversations")
        max_run = cur.fetchone()[0]
        if max_run:
            query += " AND run_id = %s"
            params.append(max_run)
    elif data_filter == 3:  # Today
        query += " AND created_at >= CURRENT_DATE"
    elif data_filter == 4:  # This week
        query += " AND created_at >= date_trunc('week', CURRENT_DATE)"
    
    if quality_threshold is not None:
        query += " AND quality_score >= %s"
        params.append(quality_threshold)
    
    query += " ORDER BY created_at"
    
    if limit:
        query += " LIMIT %s"
        params.append(limit)
    
    cur.execute(query, params)
    conversations = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return conversations

def generate_filename(conversation_id, created_at):
    """Generate LEX-compatible filename with date"""
    date_str = created_at.strftime("%Y-%m-%d")
    return f"conversation_{date_str}_{conversation_id[:8]}.json"

def load_pii_config(config_path="pii_scrubber/config.yaml"):
    """Load PII scrubbing configuration"""
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        # Return defaults if config file not found
        return {
            'default_mode': 'safe',
            'default_strategy': 'llm',
            'llm': {
                'endpoint': 'http://127.0.0.1:11434/api/generate',
                'model': 'redactor-7b-gguf',
                'timeout_s': 10
            },
            'scrub': {'placeholder_style': 'angle'},
            'report': {'enable': True, 'path': 'out/PII_REPORT.json'}
        }

def export_conversations(conversations, output_dir, batch_size=100, pii_mode="safe", pii_strategy="llm", pii_config=None, dry_run=False, strict=False, fail_on_artifacts=False, filename_date=None):
    """Export conversations to LEX format with PII scrubbing"""
    output_path = Path(output_dir)
    if not dry_run:
        output_path.mkdir(parents=True, exist_ok=True)
    
    exported_count = 0
    skipped_count = 0
    scrubbed_count = 0
    artifact_count = 0
    pii_stats = {}
    
    if pii_config is None:
        pii_config = load_pii_config()
    
    # Initialize Lex validator
    validator = LexValidator()
    
    print(f"Exporting {len(conversations)} conversations to {output_dir}")
    print(f"PII mode: {pii_mode}, strategy: {pii_strategy}")
    print(f"Strict mode: {strict}, Fail on artifacts: {fail_on_artifacts}")
    
    for i, (conv_id, content, quality_score, created_at, model_name) in enumerate(conversations):
        try:
            # Parse stored JSON content
            if isinstance(content, str):
                conversation_data = json.loads(content)
            else:
                conversation_data = content
            
            # Run Lex V2 validation
            validation_report = validator.run_all_validations(conversation_data)
            
            if not validation_report["valid"]:
                if strict:
                    print(f"\nSTRICT MODE: Validation failed for {conv_id[:8]}")
                    for error in validation_report["errors"]:
                        print(f"  ERROR: {error}")
                    raise LexValidationError(f"Validation failed in strict mode: {validation_report['errors']}")
                else:
                    print(f"Auto-fixing validation issues for {conv_id[:8]}...")
                    conversation_data = fix_lex_object(conversation_data, pii_mode)
            
            # Check for artifacts
            if validation_report["artifact_count"] > 0:
                if fail_on_artifacts:
                    raise LexValidationError(f"Artifact lines found in {conv_id[:8]} (fail-on-artifacts enabled)")
                else:
                    print(f"Removing {validation_report['artifact_count']} artifact lines from {conv_id[:8]}...")
                    conversation_data, removed = validator.remove_artifacts(conversation_data)
                    artifact_count += removed
            
            # Create date-based subdirectory
            date_str = created_at.strftime("%Y-%m-%d")
            date_dir = output_path / date_str
            date_dir.mkdir(exist_ok=True)
            
            # Generate Lex-compliant filename
            contact_id = conversation_data.get("CustomerMetadata", {}).get("ContactId", conv_id)
            filename = generate_lex_filename(contact_id, filename_date or created_at.strftime("%Y-%m-%d"))
            file_path = date_dir / filename
            
            # Validate filename has date
            filename_valid, filename_msg = validator.validate_filename_date(filename)
            if not filename_valid and strict:
                raise LexValidationError(f"Filename validation failed: {filename_msg}")
            
            # Apply PII scrubbing to transcript content
            scrubbed_any = False
            if pii_mode == "safe":
                print(f"Processing conversation {i+1}/{len(conversations)} ({conv_id[:8]}) - PII scrubbing...", end=" ")
                for turn_idx, turn in enumerate(conversation_data.get("Transcript", [])):
                    original_content = turn.get("Content", "")
                    try:
                        # Configure fallback behavior
                        config_with_fallback = pii_config.copy()
                        config_with_fallback['fallback_to_regex'] = pii_strategy != "llm"
                        
                        scrubbed_content = scrub_text(original_content, pii_mode, pii_strategy, config_with_fallback)
                        turn["Content"] = scrubbed_content
                        
                        if scrubbed_content != original_content:
                            scrubbed_count += 1
                            scrubbed_any = True
                            # Track PII types found
                            if PII_AVAILABLE:
                                from pii_scrubber.engine import detect_pii_regex
                                pii_found = detect_pii_regex(original_content)
                                for pii_type, matches in pii_found.items():
                                    if matches:
                                        pii_stats[pii_type] = pii_stats.get(pii_type, 0) + len(matches)
                    
                    except LLMUnavailableError as e:
                        if pii_strategy == "llm" and not config_with_fallback.get('fallback_to_regex', True):
                            print(f"\nERROR: SAFE mode requires a working local LLM. {e}")
                            print("Start LLM server or rerun with --pii-strategy regex or --mode raw.")
                            return 0, len(conversations)
                        else:
                            print(f"\nWarning: LLM unavailable, using original content: {e}")
                print("+")
            
            # Update ContentMetadata based on actual scrubbing
            if pii_mode == "safe" and scrubbed_any:
                conversation_data["ContentMetadata"]["Output"] = "Redacted"
            else:
                conversation_data["ContentMetadata"]["Output"] = "Raw"
            
            if dry_run:
                print(f"[DRY RUN] Would write: {file_path}")
            else:
                # Write conversation file using canonical serializer
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(serialize_canonical_lex(conversation_data))
            
            exported_count += 1
            
            # Progress update
            if (i + 1) % batch_size == 0:
                print(f"\n--- Progress: {i + 1}/{len(conversations)} conversations exported ---")
            elif pii_mode != "safe":  # Only show for non-PII mode since PII mode shows per-conversation
                if (i + 1) % 10 == 0:
                    print(f"Processed {i + 1}/{len(conversations)}...")
        
        except Exception as e:
            print(f"Error exporting conversation {conv_id[:8]}: {e}")
            skipped_count += 1
    
    # Create summary file
    summary = {
        "export_date": datetime.now().isoformat(),
        "total_conversations": len(conversations),
        "exported_count": exported_count,
        "skipped_count": skipped_count,
        "scrubbed_utterances": scrubbed_count,
        "artifact_lines_removed": artifact_count,
        "pii_mode": pii_mode,
        "pii_strategy": pii_strategy,
        "pii_stats": pii_stats,
        "strict_mode": strict,
        "output_directory": str(output_path)
    }
    
    if not dry_run:
        with open(output_path / "export_summary.json", 'w') as f:
            json.dump(summary, f, indent=2)
        
        # Write PII report if enabled
        if pii_config.get('report', {}).get('enable', True):
            report_path = Path(pii_config['report'].get('path', 'out/PII_REPORT.json'))
            report_path.parent.mkdir(parents=True, exist_ok=True)
            
            pii_report = {
                "export_date": datetime.now().isoformat(),
                "totals": {
                    "files_processed": exported_count,
                    "utterances_total": sum(len(conv[1].get('Transcript', [])) for conv in conversations if isinstance(conv[1], dict)),
                    "scrubbed_utterances": scrubbed_count,
                    "strategy_used": pii_strategy
                },
                "failures": {
                    "files_failed": skipped_count,
                    "reason": "validation_failed"
                },
                "sample_counts": pii_stats
            }
            
            with open(report_path, 'w') as f:
                json.dump(pii_report, f, indent=2)
    
    print(f"\nExport complete:")
    print(f"  Exported: {exported_count}")
    print(f"  Skipped: {skipped_count}")
    print(f"  Output: {output_path}")
    print(f"  Summary: {output_path}/export_summary.json")
    
    return exported_count, skipped_count

def validate_lex_format(conversation_data):
    """Validate conversation matches LEX format requirements"""
    required_fields = ["Participants", "Version", "ContentMetadata", "CustomerMetadata", "Transcript"]
    
    # Check top-level fields
    for field in required_fields:
        if field not in conversation_data:
            return False
    
    # Check participants
    participants = conversation_data.get("Participants", [])
    if not participants:
        return False
    
    participant_ids = set()
    for participant in participants:
        if "ParticipantId" not in participant or "ParticipantRole" not in participant:
            return False
        if participant["ParticipantRole"] not in ["AGENT", "CUSTOMER"]:
            return False
        participant_ids.add(participant["ParticipantId"])
    
    # Check transcript
    transcript = conversation_data.get("Transcript", [])
    if not transcript:
        return False
    
    for turn in transcript:
        if "ParticipantId" not in turn or "Id" not in turn or "Content" not in turn:
            return False
        if turn["ParticipantId"] not in participant_ids:
            return False
    
    return True

def main():
    parser = argparse.ArgumentParser(description="Export conversations to LEX format with PII scrubbing")
    parser.add_argument("--output-dir", default="lex_export", help="Output directory")
    parser.add_argument("--quality-threshold", type=float, help="Minimum quality score")
    parser.add_argument("--limit", type=int, help="Maximum conversations to export")
    parser.add_argument("--batch-size", type=int, default=100, help="Progress update interval")
    parser.add_argument("--all", action="store_true", help="Export all conversations")
    parser.add_argument("--data-filter", type=int, choices=[1,2,3,4], help="Data filter: 1=all, 2=last run, 3=today, 4=this week")
    
    # PII scrubbing arguments
    parser.add_argument("--mode", choices=["safe", "raw"], help="PII scrubbing mode")
    parser.add_argument("--pii-strategy", choices=["llm", "regex", "off"], help="PII scrubbing strategy")
    parser.add_argument("--llm-endpoint", help="Override LLM endpoint URL")
    parser.add_argument("--llm-model", help="Override LLM model name")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing files")
    parser.add_argument("--report", help="Override PII report path")
    parser.add_argument("--force-unsafe", action="store_true", help="Allow strategy=off in safe mode")
    
    # Lex V2 compliance arguments
    parser.add_argument("--strict", action="store_true", help="Fail on any validation error instead of auto-fixing")
    parser.add_argument("--fail-on-artifacts", action="store_true", help="Fail if artifact lines found")
    parser.add_argument("--filename-date", help="Override filename date (YYYY-MM-DD format)")
    
    args = parser.parse_args()
    
    # Show menu if no data filter specified
    data_filter = args.data_filter
    if not data_filter:
        data_filter = show_data_menu()
        if data_filter is None:
            return 1
    
    # Load configurations
    db_config = load_db_config()
    pii_config = load_pii_config()
    
    # Determine PII settings
    pii_mode = args.mode or pii_config.get('default_mode', 'safe')
    pii_strategy = args.pii_strategy or pii_config.get('default_strategy', 'llm')
    
    # Override LLM settings if provided
    if args.llm_endpoint:
        pii_config['llm']['endpoint'] = args.llm_endpoint
    if args.llm_model:
        pii_config['llm']['model'] = args.llm_model
    if args.report:
        pii_config['report']['path'] = args.report
    
    # Check PII availability
    if not PII_AVAILABLE and pii_mode == "safe":
        print("ERROR: PII scrubber not available. Cannot use safe mode without PII protection.")
        print("Options:")
        print("  1. Install PII scrubber dependencies")
        print("  2. Use raw mode explicitly: --mode raw")
        return 1
    
    # Validate PII settings
    if pii_mode == "safe" and pii_strategy == "off" and not args.force_unsafe:
        print("ERROR: Cannot use strategy=off in safe mode. Use --force-unsafe or change strategy.")
        return 1
    
    print(f"Connecting to database: {db_config['host']}:{db_config['port']}/{db_config['database']}")
    
    # Set quality threshold
    quality_threshold = args.quality_threshold
    if not args.all and quality_threshold is None:
        quality_threshold = 0.5  # Default minimum quality
        print(f"Using default quality threshold: {quality_threshold}")
    
    try:
        # Fetch conversations
        filter_names = {1: "all data", 2: "last run", 3: "today", 4: "this week"}
        print(f"Fetching conversations from database ({filter_names.get(data_filter, 'unknown filter')})...")
        conversations = get_conversations(db_config, quality_threshold, args.limit, data_filter)
        
        if not conversations:
            print("No conversations found matching criteria")
            return
        
        print(f"Found {len(conversations)} conversations")
        
        # Export conversations with PII scrubbing and Lex V2 compliance
        exported, skipped = export_conversations(
            conversations, args.output_dir, args.batch_size,
            pii_mode, pii_strategy, pii_config, args.dry_run,
            args.strict, args.fail_on_artifacts, args.filename_date
        )
        
        if exported > 0:
            print(f"\nSuccessfully exported {exported} conversations for LEX training")
            print(f"Files ready in: {args.output_dir}")
        else:
            print("ERROR: No conversations were exported")
    
    except KeyboardInterrupt:
        print("\n\nExport cancelled by user.")
        return 1
    except LexValidationError as e:
        print(f"\nLEX VALIDATION ERROR: {e}")
        return 2
    except Exception as e:
        print(f"ERROR: Export failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    try:
        exit(main())
    except KeyboardInterrupt:
        print("\n\nExport cancelled by user.")
        exit(1)