import psycopg2
import os
from dotenv import load_dotenv

# 🔄 Load environment variables from .env file automatically
load_dotenv()

# 🔧 Database connection config
DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "127.0.0.1"),
    "port": int(os.getenv("POSTGRES_PORT", 5432)),
    "dbname": os.getenv("POSTGRES_DB", "comdex"),
    "user": os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD"),  # Securely pulled from .env or environment
}

# 📡 Connection wrapper
def connect():
    try:
        return psycopg2.connect(**DB_CONFIG)
    except psycopg2.Error as e:
        print(f"[ERROR] Could not connect to database: {e}")
        raise

# ✍️ Insert fork record
def insert_fork(fork_id: str, parent_wave_id: str, sqi_score: float):
    try:
        with connect() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO forks (id, parent_wave_id, sqi_score)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (id) DO NOTHING;
                """, (fork_id, parent_wave_id, sqi_score))
            conn.commit()
            print(f"[✓] Inserted fork: {fork_id}")
    except Exception as e:
        print(f"[ERROR] Failed to insert fork: {e}")

# 🔍 Query all forks
def query_all_forks():
    try:
        with connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM forks ORDER BY sqi_score DESC;")
                rows = cur.fetchall()
                return rows
    except Exception as e:
        print(f"[ERROR] Failed to query forks: {e}")
        return []