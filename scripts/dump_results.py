#!/usr/bin/env python3
"""
Dump Results - Export all conversations to text file
"""

import psycopg2
import json
from datetime import datetime

def dump_conversations():
    """Dump all conversations to text file"""
    db_config = {
        'host': 'EPM_DELL',
        'port': 5432,
        'database': 'calllab',
        'user': 'postgres',
        'password': 'pass'
    }
    
    try:
        conn = psycopg2.connect(**db_config)
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return
    
    cur = conn.cursor()
    
    # Get all conversations with scenario info
    cur.execute("""
        SELECT c.id, c.created_at, s.name as scenario_name, c.content, c.quality_score
        FROM conversations c
        JOIN scenarios s ON c.scenario_id = s.id
        ORDER BY c.created_at DESC
    """)
    conversations = cur.fetchall()
    
    cur.close()
    conn.close()
    
    if not conversations:
        print("📭 No conversations found")
        return
    
    # Create output file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"conversation_dump_{timestamp}.txt"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write(f"CONVERSATION DUMP - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total Conversations: {len(conversations)}\n")
        f.write("=" * 80 + "\n\n")
        
        for conv_id, created_at, scenario_name, content_json, quality_score in conversations:
            try:
                content = json.loads(content_json)
                
                f.write(f"Conversation ID: {conv_id}\n")
                f.write(f"Created: {created_at}\n")
                f.write(f"Scenario: {scenario_name}\n")
                f.write(f"Quality Score: {quality_score}\n")
                f.write("-" * 60 + "\n")
                
                # Write transcript
                for turn in content.get("Transcript", []):
                    participant = "CUSTOMER" if turn["ParticipantId"] == "C1" else "AGENT"
                    f.write(f"{participant}: {turn['Content']}\n")
                
                f.write("\n" + "=" * 80 + "\n\n")
                
            except json.JSONDecodeError:
                f.write(f"❌ Error parsing conversation {conv_id}\n\n")
    
    print(f"✅ Dumped {len(conversations)} conversations to: {output_file}")

if __name__ == "__main__":
    dump_conversations()