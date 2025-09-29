# backend/modules/codex/instruction_registry_loader.py
import yaml
import os

REGISTRY_PATH = os.path.join("docs", "CodexLang_Instruction", "instruction_registry.yaml")

def load_registry():
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

if __name__ == "__main__":
    print(load_registry())