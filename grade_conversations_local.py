#!/usr/bin/env python3
"""Local conversation grader without OpenAI dependency"""

import psycopg2
import json
import uuid
from datetime import datetime

def grade_conversation_local(conversation_text):
    """Simple local grading based on conversation characteristics"""
    
    # Basic quality metrics
    lines = conversation_text.strip().split('\n')
    word_count = len(conversation_text.split())
    
    # Realness score (6-9 based on length and structure)
    if word_count > 100 and len(lines) > 10:
        realness_score = 8
    elif word_count > 50 and len(lines) > 5:
        realness_score = 7
    else:
        realness_score = 6
    
    # Healthcare validation
    healthcare_keywords = ['appointment', 'doctor', 'checkup', 'medical', 'health', 'patient', 'clinic', 'schedule']
    healthcare_valid = any(keyword in conversation_text.lower() for keyword in healthcare_keywords)
    
    # Coherence (7-9 based on structure)
    coherence_score = 8 if len(lines) > 8 else 7
    
    # Naturalness (7-8 based on conversational patterns)
    naturalness_score = 8 if '?' in conversation_text and word_count > 80 else 7
    
    # Overall score (average of other scores)
    overall_score = round((realness_score + coherence_score + naturalness_score) / 3)
    
    return {
        "realness_score": realness_score,
        "coherence_score": coherence_score,
        "naturalness_score": naturalness_score,
        "overall_score": overall_score,
        "healthcare_valid": healthcare_valid,
        "brief_feedback": f"Local grading: {word_count} words, {len(lines)} turns",
        "grading_error": None
    }

def grade_database_conversations(grader_type="local", progress_callback=None):
    """Grade conversations from database using local grading"""
    
    db_config = {
        'host': 'EPM_DELL',
        'port': 5432,
        'database': 'calllab',
        'user': 'postgres',
        'password': 'pass'
    }
    
    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()
    
    # Get ungraded conversations
    cur.execute("""
        SELECT c.id, c.content
        FROM conversations c
        WHERE NOT EXISTS (SELECT 1 FROM conversation_grades WHERE conversation_id = c.id)
        ORDER BY c.created_at DESC
        LIMIT 50
    """)
    
    conversations = cur.fetchall()
    print(f"Found {len(conversations)} conversations to grade")
    
    graded_count = 0
    total_conversations = len(conversations)
    
    for i, (conv_id, content) in enumerate(conversations, 1):
        try:
            # Parse conversation content
            content_data = json.loads(content) if isinstance(content, str) else content
            
            conversation_text = ""
            if "Transcript" in content_data:
                for turn in content_data["Transcript"]:
                    conversation_text += f"{turn.get('Content', '')}\n"
            else:
                conversation_text = str(content_data)
            
            if not conversation_text.strip():
                continue
            
            # Grade conversation locally (simple fallback)
            grades = grade_conversation_local(conversation_text)
            
            # Store grades in database
            grade_id = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO conversation_grades 
                (id, conversation_id, realness_score, coherence_score, naturalness_score, 
                 overall_score, healthcare_valid, brief_feedback, grading_error, graded_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                grade_id, conv_id,
                grades["realness_score"],
                grades["coherence_score"], 
                grades["naturalness_score"],
                grades["overall_score"],
                grades["healthcare_valid"],
                grades["brief_feedback"],
                grades["grading_error"],
                datetime.now()
            ))
            
            conn.commit()
            graded_count += 1
            

            
            print(f"  Graded {conv_id[:8]}: R={grades['realness_score']}, O={grades['overall_score']}")
            
        except Exception as e:
            print(f"  Error processing conversation {conv_id[:8]}: {e}")
            conn.rollback()
            continue
    
    cur.close()
    conn.close()
    
    print(f"Completed grading {graded_count} conversations")
    return graded_count

if __name__ == "__main__":
    grade_database_conversations()