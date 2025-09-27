#!/usr/bin/env python3
"""
View generated conversation results
"""

import psycopg2
import json

DB_CONFIG = {
    'host': 'EPM_DELL',
    'port': 5432,
    'database': 'calllab',
    'user': 'postgres',
    'password': 'pass'
}

def view_results():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return
    
    cur = conn.cursor()
    
    # Get conversation count
    cur.execute("SELECT COUNT(*) FROM conversations")
    count = cur.fetchone()[0]
    print(f"📊 Total conversations: {count}")
    
    if count == 0:
        print("No conversations generated yet")
        return
    
    # Get recent conversations
    cur.execute("""
        SELECT c.id, s.name, c.quality_score, c.created_at, c.content
        FROM conversations c
        JOIN scenarios s ON c.scenario_id = s.id
        ORDER BY c.created_at DESC
        LIMIT 2
    """)
    conversations = cur.fetchall()
    
    cur.close()
    
    print("\n🗣️ Recent Conversations:")
    for conv_id, scenario, quality, created_at, content_json in conversations:
        print(f"\n--- {conv_id[:8]} | {scenario} | Quality: {quality} ---")
        
        try:
            content = json.loads(content_json)
            transcript = content.get("Transcript", [])
            
            # Show first few turns
            for i, turn in enumerate(transcript[:6]):
                role = "Customer" if turn["ParticipantId"] == "C1" else "Agent"
                print(f"{role}: {turn['Content']}")
            
            if len(transcript) > 6:
                print(f"... ({len(transcript) - 6} more turns)")
                
        except json.JSONDecodeError:
            print("Error parsing conversation content")
    
    conn.close()

def view_conversation(conv_id):
    """View a specific conversation in full"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT c.content, s.name
        FROM conversations c
        JOIN scenarios s ON c.scenario_id = s.id
        WHERE c.id LIKE %s
    """, (f"{conv_id}%",))
    result = cur.fetchone()
    
    cur.close()
    
    if not result:
        print(f"❌ Conversation not found: {conv_id}")
        return
    
    content_json, scenario = result
    
    try:
        content = json.loads(content_json)
        transcript = content.get("Transcript", [])
        
        print(f"\n🗣️ Full Conversation - {scenario}")
        print("=" * 50)
        
        for turn in transcript:
            role = "Customer" if turn["ParticipantId"] == "C1" else "Agent"
            print(f"{role}: {turn['Content']}")
            
    except json.JSONDecodeError:
        print("Error parsing conversation content")
    
    conn.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # View specific conversation
        view_conversation(sys.argv[1])
    else:
        # View summary
        view_results()