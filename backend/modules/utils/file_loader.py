import json

def load_dc_container(path: str):
    with open(path, 'r') as f:
        return json.load(f)