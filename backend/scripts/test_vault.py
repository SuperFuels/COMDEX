from backend.modules.consciousness.vault_engine import PrivacyVault
import os
from dotenv import load_dotenv

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

# Load .env.local if not already loaded
load_dotenv()

vault = PrivacyVault()
test_key = "dream_001"
test_value = "This is a private dream reflection."

# ✅ Test store
vault.store(test_key, test_value)
print(f"Stored: {vault.retrieve(test_key)}")

# ✅ Test access
override_key = os.getenv("KEVIN_MASTER_KEY", "")
if vault.has_access(override_key):
    print("🔐 Access granted via KEVIN_MASTER_KEY")
else:
    print("🚫 Access denied")

# ✅ Test delete
vault.delete(test_key)
print(f"After delete: {vault.retrieve(test_key)}")