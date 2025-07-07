from sqlalchemy import create_engine, text

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

# make sure this matches your alembic.ini URL
engine = create_engine("postgresql+psycopg2://comdex:Wn8smx123@localhost:5432/comdex")

with engine.begin() as conn:
    # force Alembic to think fc8e33aeeef9 is current
    conn.execute(text("UPDATE alembic_version SET version_num = 'fc8e33aeeef9'"))
print("Stamped DB at fc8e33aeeef9")
