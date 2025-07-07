import os

# ✅ DNA Switch
from backend.modules.dna.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

ROOT_DIR = 'backend'
OLD_IMPORT_PREFIX = 'modules'
NEW_IMPORT_PREFIX = 'backend.modules'

def fix_imports_in_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    new_content = content

    # Replace "from modules." with "from backend.modules."
    new_content = new_content.replace(f'from {OLD_IMPORT_PREFIX}.', f'from {NEW_IMPORT_PREFIX}.')

    # Replace "import modules." with "import backend.modules."
    new_content = new_content.replace(f'import {OLD_IMPORT_PREFIX}.', f'import {NEW_IMPORT_PREFIX}.')

    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f'Fixed imports in: {filepath}')

def main():
    for subdir, _, files in os.walk(ROOT_DIR):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(subdir, file)
                fix_imports_in_file(filepath)

if __name__ == '__main__':
    main()