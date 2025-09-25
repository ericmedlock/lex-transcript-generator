import os
import psycopg2
import redis
from dotenv import load_dotenv

# Load .env file
load_dotenv()

db_url = os.getenv("DATABASE_URL")
redis_url = os.getenv("REDIS_URL")

print("=== Infra Check ===")

# Check Postgres
try:
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    cur.execute("SELECT version();")
    version = cur.fetchone()[0]
    print(f"Postgres: Connected OK ({version})")
    cur.close()
    conn.close()
except Exception as e:
    print("Postgres: FAILED ->", e)

# Check Redis
try:
    r = redis.Redis.from_url(redis_url)
    pong = r.ping()
    if pong:
        print("Redis: Connected OK (PONG)")
    else:
        print("Redis: FAILED (no PONG)")
except Exception as e:
    print("Redis: FAILED ->", e)

print("===================")
