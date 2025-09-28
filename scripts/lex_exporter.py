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
            print("\nExiting...")
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
                'timeout_s': 20
            },
            'scrub': {'placeholder_style': 'angle'},
            'report': {'enable': True, 'path': 'out/PII_REPORT.json'}
        }

def export_conversations(conversations, output_dir, batch_size=100, pii_mode="safe", pii_strategy="llm", pii_config=None, dry_run=False):
    """Export conversations to LEX format with PII scrubbing"""
    output_path = Path(output_dir)
    if not dry_run:
        output_path.mkdir(parents=True, exist_ok=True)
    
    exported_count = 0
    skipped_count = 0
    scrubbed_count = 0
    pii_stats = {}
    
    if pii_config is None:
        pii_config = load_pii_config()
    
    print(f"Exporting {len(conversations)} conversations to {output_dir}")
    print(f"PII mode: {pii_mode}, strategy: {pii_strategy}")
    
    for i, (conv_id, content, quality_score, created_at, model_name) in enumerate(conversations):
        try:
            # Parse stored JSON content
            if isinstance(content, str):
                conversation_data = json.loads(content)
            else:
                conversation_data = content
            
            # Validate LEX format
            if not validate_lex_format(conversation_data):
                print(f"Skipping invalid conversation: {conv_id[:8]}")
                skipped_count += 1
                continue
            
            # Create date-based subdirectory
            date_str = created_at.strftime("%Y-%m-%d")
            date_dir = output_path / date_str
            date_dir.mkdir(exist_ok=True)
            
            # Generate filename
            filename = generate_filename(conv_id, created_at)
            file_path = date_dir / filename
            
            # Apply PII scrubbing to transcript content
            if pii_mode == "safe":
                for turn in conversation_data.get("Transcript", []):
                    original_content = turn.get("Content", "")
                    try:
                        # Configure fallback behavior
                        config_with_fallback = pii_config.copy()
                        config_with_fallback['fallback_to_regex'] = pii_strategy != "llm"  # Only fallback if not explicitly requested LLM
                        
                        scrubbed_content = scrub_text(original_content, pii_mode, pii_strategy, config_with_fallback)
                        turn["Content"] = scrubbed_content
                        
                        if scrubbed_content != original_content:
                            scrubbed_count += 1
                            # Track PII types found
                            pii_found = detect_pii_regex(original_content)
                            for pii_type, matches in pii_found.items():
                                if matches:
                                    pii_stats[pii_type] = pii_stats.get(pii_type, 0) + len(matches)
                    
                    except LLMUnavailableError as e:
                        if pii_strategy == "llm" and not config_with_fallback.get('fallback_to_regex', True):
                            print(f"ERROR: SAFE mode requires a working local LLM. {e}")
                            print("Start LLM server or rerun with --pii-strategy regex or --mode raw.")
                            return 0, len(conversations)
                        else:
                            # This shouldn't happen due to fallback logic, but handle gracefully
                            print(f"Warning: LLM unavailable, using original content: {e}")
                
                # Update ContentMetadata
                conversation_data["ContentMetadata"]["Output"] = "Redacted"
            else:
                # Raw mode
                conversation_data["ContentMetadata"]["Output"] = "Raw"
            
            if dry_run:
                print(f"[DRY RUN] Would write: {file_path}")
            else:
                # Write conversation file
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(conversation_data, f, indent=2, ensure_ascii=False)
            
            exported_count += 1
            
            # Progress update
            if (i + 1) % batch_size == 0:
                print(f"Exported {i + 1}/{len(conversations)} conversations...")
        
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
        "pii_mode": pii_mode,
        "pii_strategy": pii_strategy,
        "pii_stats": pii_stats,
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
        print("  1. Install PII scrubber: pip install pyyaml")
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
        
        # Export conversations with PII scrubbing
        exported, skipped = export_conversations(
            conversations, args.output_dir, args.batch_size,
            pii_mode, pii_strategy, pii_config, args.dry_run
        )
        
        if exported > 0:
            print(f"\nSuccessfully exported {exported} conversations for LEX training")
            print(f"Files ready in: {args.output_dir}")
        else:
            print("ERROR: No conversations were exported")
    
    except Exception as e:
        print(f"ERROR: Export failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())