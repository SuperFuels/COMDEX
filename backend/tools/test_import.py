# File: backend/tools/test_import.py
from backend.modules.glyphvault import vault_bridge

print("FILE LOADED:", vault_bridge.__file__)
print("METHOD EXISTS:", hasattr(vault_bridge.ContainerVaultManager, "load_container_by_id"))