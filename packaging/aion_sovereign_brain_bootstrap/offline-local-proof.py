#!/usr/bin/env python3
"""Useful, provider-free local proof for an extracted offline bootstrap."""
import json
import os
import sys
import urllib.request


def main():
    if any(os.environ.get(name) for name in ("OPENAI_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY")):
        raise SystemExit("Paid-provider keys must be absent during the offline proof")
    prompt = {
        "instruction": "Return JSON only with keys summary and tasks. Keep exactly two short tasks.",
        "notes": "Customer meeting agreed to inspect the stock count on Friday and prepare the supplier comparison before Monday.",
    }
    request = urllib.request.Request(
        os.environ.get("OLLAMA_URL", "http://127.0.0.1:11455/api/generate"),
        data=json.dumps({"model": "gemma3:1b", "prompt": json.dumps(prompt), "stream": False, "format": "json", "options": {"temperature": 0, "num_predict": 96}}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=720) as response:
        result = json.loads(response.read())
    output = json.loads(result["response"])
    if not isinstance(output.get("summary"), str) or len(output.get("tasks") or []) != 2:
        raise SystemExit("Local model did not return the required useful structure")
    print(json.dumps({"ok": True, "provider": "local_ollama", "model": "gemma3:1b", "output": output, "paid_api_used": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
