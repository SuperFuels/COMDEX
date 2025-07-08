from backend.modules.aion.token_engine import TokenEngine

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

if __name__ == "__main__":
    t = TokenEngine()
    t.mint("aion", 50)
    print("✅ Minted 50 $STK for AION.")
