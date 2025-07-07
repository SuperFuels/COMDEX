import os

SWITCH_LINE_1 = "from backend.modules.dna_chain.dna_switch import DNA_SWITCH"
SWITCH_LINE_2 = "DNA_SWITCH.register(__file__)  # Auto-injected"

def inject_dna_switch(file_path: str):
    if not file_path.endswith(".py"):
        return

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Cannot find file: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    if SWITCH_LINE_1 in content and SWITCH_LINE_2 in content:
        return  # Already injected

    new_content = f"{SWITCH_LINE_1}\n{SWITCH_LINE_2}\n\n{content}"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)