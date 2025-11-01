#!/usr/bin/env python3
importos
importpg8000

# ✅ DNA Switch
frombackend.modules.dna.dna_switchimportDNA_SWITCH
DNA_SWITCH.register(__file__)# Allow tracking + upgrades to this file

# - configure (or override with env vars) -
USER=os.getenv("DB_USER","comdex")
PASS=os.getenv("DB_PASS","Wn8smx123")
HOST=os.getenv("DB_HOST","127.0.0.1")
PORT=int(os.getenv("DB_PORT","5432"))
DB=os.getenv("DB_NAME","comdex")

# - connect via pg8000's DB-API interface -
conn=pg8000.connect(
user=USER,
password=PASS,
host=HOST,
port=PORT,
database=DB
)
cur=conn.cursor()

# 1) ping the server
cur.execute("SELECT NOW();")
now=cur.fetchone()[0]
print("DB time:",now)

# 2) sample up to 5 users
cur.execute("SELECT id, email, created_at FROM users LIMIT 5;")
rows=cur.fetchall()
ifrows:
    print("\nSample users:")
for(uid,email,created_at)inrows:
        print(f" * {uid}: {email} @ {created_at}")
else:
    print("\nNo users found in table!")

cur.close()
conn.close()
