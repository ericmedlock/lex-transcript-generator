#!/usr/bin/env python3

import psycopg2

DB_CONFIG = {
    'host': 'EPM_DELL',
    'port': 5432,
    'database': 'calllab',
    'user': 'postgres',
    'password': 'pass'
}

def count_conversations():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM conversations")
    count = cur.fetchone()[0]
    cur.close()
    conn.close()
    return count

if __name__ == "__main__":
    print(count_conversations())