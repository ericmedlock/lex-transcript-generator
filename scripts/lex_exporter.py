#!/usr/bin/env python3
"""
LEX Exporter - Export conversations to Amazon LEX Automated Chatbot Designer format
"""

import json
import os
import psycopg2
import argparse
from datetime import datetime, date
from pathlib import Path

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

def get_conversations(db_config, quality_threshold=None, limit=None):
    """Fetch conversations from database"""
    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()
    
    query = """
        SELECT id, content, quality_score, created_at, model_name
        FROM conversations 
        WHERE content IS NOT NULL
    """
    params = []
    
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

def export_conversations(conversations, output_dir, batch_size=100):
    """Export conversations to LEX format"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    exported_count = 0
    skipped_count = 0
    
    print(f"Exporting {len(conversations)} conversations to {output_dir}")
    
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
        "output_directory": str(output_path)
    }
    
    with open(output_path / "export_summary.json", 'w') as f:
        json.dump(summary, f, indent=2)
    
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
    parser = argparse.ArgumentParser(description="Export conversations to LEX format")
    parser.add_argument("--output-dir", default="lex_export", help="Output directory")
    parser.add_argument("--quality-threshold", type=float, help="Minimum quality score")
    parser.add_argument("--limit", type=int, help="Maximum conversations to export")
    parser.add_argument("--batch-size", type=int, default=100, help="Progress update interval")
    parser.add_argument("--all", action="store_true", help="Export all conversations")
    
    args = parser.parse_args()
    
    # Load database config
    db_config = load_db_config()
    print(f"Connecting to database: {db_config['host']}:{db_config['port']}/{db_config['database']}")
    
    # Set quality threshold
    quality_threshold = args.quality_threshold
    if not args.all and quality_threshold is None:
        quality_threshold = 0.5  # Default minimum quality
        print(f"Using default quality threshold: {quality_threshold}")
    
    try:
        # Fetch conversations
        print("Fetching conversations from database...")
        conversations = get_conversations(db_config, quality_threshold, args.limit)
        
        if not conversations:
            print("No conversations found matching criteria")
            return
        
        print(f"Found {len(conversations)} conversations")
        
        # Export conversations
        exported, skipped = export_conversations(conversations, args.output_dir, args.batch_size)
        
        if exported > 0:
            print(f"\n✅ Successfully exported {exported} conversations for LEX training")
            print(f"📁 Files ready in: {args.output_dir}")
        else:
            print("❌ No conversations were exported")
    
    except Exception as e:
        print(f"❌ Export failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())