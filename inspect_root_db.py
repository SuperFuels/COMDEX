#!/usr/bin/env python3
"""
Quickly dump tables, columns & FKs from the root dev.db
"""
import os
from sqlalchemy import create_engine, inspect

# point at the root dev.db
HERE    = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(HERE, "dev.db")
db_url  = f"sqlite:///{db_path}"

print(f"Inspecting {db_url!r}\n")

engine    = create_engine(db_url)
insp      = inspect(engine)

print("All tables:")
for t in insp.get_table_names():
    print(" ", t)

if "shipments" in insp.get_table_names():
    print("\nColumns in shipments:")
    for c in insp.get_columns("shipments"):
        print("  ", c["name"], c["type"], "nullable=" + str(c["nullable"]))
    print("\nFKs on shipments:")
    for fk in insp.get_foreign_keys("shipments"):
        print("  ", fk["constrained_columns"], "→", fk["referred_table"], fk["referred_columns"])
else:
    print("\n❌ No shipments table here.")
