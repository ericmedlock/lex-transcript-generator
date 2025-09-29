#!/usr/bin/env python3
"""Check conversation data in database"""

import psycopg2
import json

def check_conversations():
    db_config = {
        'host': 'EPM_DELL',
        'port': 5432,
        'database': 'calllab',
        'user': 'postgres',
        'password': 'pass'
    }
    
    try:
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()
        
        # Get recent conversations with full content
        cur.execute("""
            SELECT id, content, model_name, generation_duration_ms, 
                   json_array_length(content::json->'Transcript') as turn_count
            FROM conversations 
            ORDER BY created_at DESC 
            LIMIT 5
        """)
        
        conversations = cur.fetchall()
        
        for i, (conv_id, content, model_name, duration_ms, turn_count) in enumerate(conversations, 1):
            print(f"\n=== Conversation {i} ===")
            print(f"ID: {conv_id[:8]}")
            print(f"Model: {model_name}")
            print(f"Duration: {duration_ms}ms")
            print(f"Turn count: {turn_count}")
            
            # Parse and show transcript
            if content:
                try:
                    conv_data = json.loads(content) if isinstance(content, str) else content
                    transcript = conv_data.get('Transcript', [])
                    
                    print(f"Transcript ({len(transcript)} turns):")
                    for turn in transcript[:6]:  # Show first 6 turns
                        role = "Customer" if turn['ParticipantId'] == 'C1' else "Agent"
                        content_text = turn['Content'][:100] + "..." if len(turn['Content']) > 100 else turn['Content']
                        print(f"  {role}: {content_text}")
                    
                    if len(transcript) > 6:
                        print(f"  ... and {len(transcript) - 6} more turns")
                        
                except Exception as e:
                    print(f"Error parsing content: {e}")
            
            print("-" * 50)
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_conversations()