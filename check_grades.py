#!/usr/bin/env python3
"""Check grading results in database"""

import psycopg2
import json
from datetime import datetime

db_config = {
    'host': 'EPM_DELL',
    'port': 5432,
    'database': 'calllab',
    'user': 'postgres',
    'password': 'pass'
}

conn = psycopg2.connect(**db_config)
cur = conn.cursor()

# Get recent grading results
cur.execute("""
    SELECT 
        conversation_id, 
        realness_score, 
        coherence_score, 
        naturalness_score, 
        overall_score, 
        healthcare_valid, 
        brief_feedback, 
        grading_error,
        graded_at
    FROM conversation_grades 
    ORDER BY graded_at DESC 
    LIMIT 20
""")

results = cur.fetchall()

print(f"Found {len(results)} grading results:")
print("-" * 80)

for row in results:
    conv_id, r_score, c_score, n_score, o_score, hc_valid, feedback, error, graded_at = row
    
    print(f"Conversation: {conv_id}")
    print(f"  Scores: R={r_score}, C={c_score}, N={n_score}, O={o_score}")
    print(f"  Healthcare Valid: {hc_valid}")
    print(f"  Feedback: {feedback}")
    if error:
        print(f"  Error: {error}")
    print(f"  Graded: {graded_at}")
    print()

# Get summary stats
cur.execute("""
    SELECT 
        COUNT(*) as total,
        AVG(realness_score) as avg_realness,
        AVG(overall_score) as avg_overall,
        COUNT(CASE WHEN healthcare_valid = true THEN 1 END) as healthcare_valid_count,
        COUNT(CASE WHEN grading_error IS NOT NULL THEN 1 END) as error_count
    FROM conversation_grades
""")

stats = cur.fetchone()
total, avg_r, avg_o, hc_count, err_count = stats

print("=" * 80)
print("SUMMARY STATISTICS:")
print(f"Total Graded: {total}")
print(f"Average Realness Score: {avg_r:.2f}" if avg_r else "Average Realness Score: N/A")
print(f"Average Overall Score: {avg_o:.2f}" if avg_o else "Average Overall Score: N/A")
print(f"Healthcare Valid: {hc_count}/{total}")
print(f"Errors: {err_count}")

cur.close()
conn.close()