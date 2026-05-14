# sync .wiki <-> .ptn forms
import json, os

def wiki_to_photon(wiki_path, ptn_path):
    with open(wiki_path) as f:
        text = f.read()

    page = {"source": text, "links": []}

    with open(ptn_path, "w") as f:
        json.dump(page, f, indent=2)

    return ptn_path


def photon_to_wiki(ptn_path, wiki_path):
    with open(ptn_path) as f:
        page = json.load(f)

    with open(wiki_path, "w") as f:
        f.write(page.get("source", ""))

    return wiki_path