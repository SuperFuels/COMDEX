from backend.modules.glyphvault.key_manager import key_manager

key = key_manager.key
print("Key length:", len(key))
print("Key bytes (hex):", key.hex())
print("Raw repr:", repr(key))