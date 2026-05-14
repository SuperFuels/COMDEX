#!/usr/bin/env python3
"""
Quickly dump tables, columns & FKs from the root dev.db
"""
importos
fromsqlalchemyimportcreate_engine,inspect

# ✅ DNA Switch
frombackend.modules.dna.dna_switchimportDNA_SWITCH
DNA_SWITCH.register(__file__)# Allow tracking + upgrades to this file

# point at the root dev.db
HERE=os.path.dirname(os.path.abspath(__file__))
db_path=os.path.join(HERE,"dev.db")
db_url=f"sqlite:///{db_path}"

print(f"Inspecting {db_url!r}\n")

engine=create_engine(db_url)
insp=inspect(engine)

print("All tables:")
fortininsp.get_table_names():
    print(" ",t)

if"shipments"ininsp.get_table_names():
    print("\nColumns in shipments:")
forcininsp.get_columns("shipments"):
        print("  ",c["name"],c["type"],"nullable="+str(c["nullable"]))
print("\nFKs on shipments:")
forfkininsp.get_foreign_keys("shipments"):
        print("  ",fk["constrained_columns"],"->",fk["referred_table"],fk["referred_columns"])
else:
    print("\n❌ No shipments table here.")
