#!/usr/bin/env python3
"""Clear all grading results from database"""

import psycopg2

db_config = {
    'host': 'EPM_DELL',
    'port': 5432,
    'database': 'calllab',
    'user': 'postgres',
    'password': 'pass'
}

conn = psycopg2.connect(**db_config)
cur = conn.cursor()

# Count existing records
cur.execute("SELECT COUNT(*) FROM conversation_grades")
count = cur.fetchone()[0]
print(f"Found {count} existing grade records")

# Clear the table
cur.execute("DELETE FROM conversation_grades")
conn.commit()

print("All grading records cleared")

cur.close()
conn.close()