from backend.modules.aion.token_engine import TokenEngine

if __name__ == "__main__":
    t = TokenEngine()
    t.mint("aion", 50)
    print("✅ Minted 50 $STK for AION.")
