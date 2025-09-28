import psycopg2
import json

conn = psycopg2.connect(host='192.168.68.60', port=5432, database='calllab', user='postgres', password='pass')
cur = conn.cursor()
cur.execute("SELECT hostname, system_metrics FROM nodes WHERE status='online'")
for row in cur.fetchall():
    print(f"{row[0]}: {row[1]}")