# 📁 backend/modules/teleport/test_teleport_trigger.py

import time
from backend.modules.teleport.portal_manager import PORTALS, create_teleport_packet
from backend.modules.glyphvault.vault_manager import VAULT
from backend.modules.glyphvault.avatar_state import set_avatar_state

# Set avatar state manually for testing
set_avatar_state({
    "level": 15,
    "roles": ["admin", "tester"],
    "trust": 100,
    "soul_signature": "testing-avatar"
})

# Replace with valid container IDs
SOURCE_CONTAINER_ID = "atom_test_01"
TARGET_CONTAINER_ID = "dream_container_42"

# Mocked valid avatar_state (normally this comes from session/auth)
MOCK_AVATAR_STATE = {
    "identity": "test_operator",
    "id": "test_operator_01",       # <-- add this
    "role": "engineer",             # <-- ensure role is valid
    "public_key": "dev_local_key",
    "clearance": "root",
    "verified": True
}

def test_teleport():
    print("🚀 Initiating teleport test...")

    # 0. Try to preload the target container
    try:
        VAULT.load_container_by_id(TARGET_CONTAINER_ID, avatar_state=MOCK_AVATAR_STATE)
        print(f"📦 Loaded target container: {TARGET_CONTAINER_ID}")
    except Exception as e:
        print(f"⚠️ Failed to load target container: {e}")

    # 1. Register portal
    portal_id = PORTALS.register_portal(source=SOURCE_CONTAINER_ID, target=TARGET_CONTAINER_ID)
    print(f"🌀 Portal registered: {portal_id}")

    # 2. Create payload with avatar state
    payload = {
        "teleport_reason": "manual_test",
        "timestamp": time.time(),
        "trigger": "debug_script",
        "note": "Testing backend teleport logic",
        "avatar_state": MOCK_AVATAR_STATE
    }

    # 3. Create packet
    packet = create_teleport_packet(
        portal_id=portal_id,
        container_id=SOURCE_CONTAINER_ID,
        payload=payload
    )

    # 4. Teleport
    success = PORTALS.teleport(packet)

    # 5. Print result
    print(f"✅ Teleport result: {'SUCCESS' if success else 'FAILURE'}")

if __name__ == "__main__":
    test_teleport()