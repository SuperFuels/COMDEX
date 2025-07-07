#!/usr/bin/env python3
import os
import pg8000

# ✅ DNA Switch
from backend.modules.dna.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

# — configure (or override with env vars) —
USER = os.getenv("DB_USER", "comdex")
PASS = os.getenv("DB_PASS", "Wn8smx123")
HOST = os.getenv("DB_HOST", "127.0.0.1")
PORT = int(os.getenv("DB_PORT", "5432"))
DB   = os.getenv("DB_NAME", "comdex")

# — connect via pg8000’s DB-API interface —
conn = pg8000.connect(
    user=USER,
    password=PASS,
    host=HOST,
    port=PORT,
    database=DB
)
cur = conn.cursor()

# 1) ping the server
cur.execute("SELECT NOW();")
now = cur.fetchone()[0]
print("DB time:", now)

# 2) sample up to 5 users
cur.execute("SELECT id, email, created_at FROM users LIMIT 5;")
rows = cur.fetchall()
if rows:
    print("\nSample users:")
    for (uid, email, created_at) in rows:
        print(f" • {uid}: {email} @ {created_at}")
else:
    print("\nNo users found in table!")

cur.close()
conn.close()
