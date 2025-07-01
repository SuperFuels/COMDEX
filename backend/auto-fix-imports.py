import os
import re

BASE_DIR = 'backend'

replacements = [
    (re.compile(r'from \.\.database import'), 'from database import'),
    (re.compile(r'from backend\.database import'), 'from database import'),
    (re.compile(r'from \.\.models'), 'from models'),
    (re.compile(r'from backend\.models'), 'from models'),
    (re.compile(r'from \.\.modules'), 'from modules'),
]

def process_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        print(f'Skipping non-utf8 file: {filepath}')
        return

    original_content = content
    for pattern, replacement in replacements:
        content = pattern.sub(replacement, content)

    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'Fixed imports in: {filepath}')

def main():
    for root, dirs, files in os.walk(BASE_DIR):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                process_file(filepath)

if __name__ == '__main__':
    main()