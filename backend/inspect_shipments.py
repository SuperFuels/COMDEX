#!/usr/bin/env python3
"""
Inspect the 'shipments' table (and list all tables) via SQLAlchemy reflection.
"""

import os
from sqlalchemy import create_engine, inspect

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

# point at the same dev.db your Alembic uses
HERE = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(HERE, "dev.db")
db_url  = f"sqlite:///{db_path}"

print(f"Inspecting {db_url!r}\n")

engine    = create_engine(db_url)
inspector = inspect(engine)

# 1) list all tables
print(">>> All tables in database:")
for tbl in inspector.get_table_names():
    print("  -", tbl)

if "shipments" not in inspector.get_table_names():
    print("\n⚠️  Table 'shipments' not found. Make sure you're pointing at the right dev.db!")
    exit(1)

# 2) dump shipments columns
print("\n>>> Columns in 'shipments':")
for col in inspector.get_columns("shipments"):
    print(f"  * {col['name']}  (type={col['type']}, nullable={col['nullable']})")

# 3) dump foreign keys
print("\n\n>>> Foreign keys on 'shipments':")
fks = inspector.get_foreign_keys("shipments")
if not fks:
    print("  (none)")
else:
    for fk in fks:
        cols = fk['constrained_columns']
        ref  = f"{fk['referred_table']}({', '.join(fk['referred_columns'])})"
        print(f"  * {cols} -> {ref}")

# 4) dump indexes
print("\n\n>>> Indexes on 'shipments':")
for idx in inspector.get_indexes("shipments"):
    print(f"  * {idx['name']}: columns={idx['column_names']}, unique={idx['unique']}")
