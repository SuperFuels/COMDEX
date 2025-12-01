# debug_photon_translate.py
import requests, json

URL = "http://localhost:8080/api/photon/translate"

def translate(text: str, language: str = "photon"):
    payload = {"text": text, "language": language}
    print("POST", payload)
    r = requests.post(URL, json=payload, timeout=60)
    r.raise_for_status()
    print(json.dumps(r.json(), indent=2, ensure_ascii=False))

if __name__ == "__main__":
    sample = 'import quantum\ncontainer_id = wave ⊕ resonance\n# able sailor\nprint("hello able world")'
    translate(sample, "python")