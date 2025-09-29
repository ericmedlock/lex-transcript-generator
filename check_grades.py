#!/usr/bin/env python3
"""Check conversation grades"""

import psycopg2
import json

db_config = {
    'host': 'EPM_DELL',
    'port': 5432,
    'database': 'calllab',
    'user': 'postgres',
    'password': 'pass'
}

conn = psycopg2.connect(**db_config)
cur = conn.cursor()

cur.execute("""
    SELECT 
        c.id, 
        cg.realness_score, 
        cg.coherence_score, 
        cg.naturalness_score, 
        cg.overall_score, 
        cg.healthcare_valid, 
        cg.brief_feedback,
        LEFT(c.content::text, 200) as content_preview
    FROM conversation_grades cg 
    JOIN conversations c ON c.id = cg.conversation_id 
    ORDER BY cg.graded_at DESC 
    LIMIT 10
""")

results = cur.fetchall()

print("Recent Conversation Grades:")
print("=" * 80)

for row in results:
    conv_id, realness, coherence, naturalness, overall, healthcare, feedback, preview = row
    
    print(f"ID: {conv_id[:8]}...")
    print(f"Scores: R={realness}, C={coherence}, N={naturalness}, O={overall}")
    print(f"Healthcare Valid: {healthcare}")
    print(f"Feedback: {feedback}")
    print(f"Preview: {preview[:100]}...")
    print("-" * 40)

cur.close()
conn.close()