from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from typing import Any


DEFAULT_BASE_URL = "http://127.0.0.1:8080"


def request_json(method: str, url: str, payload: dict[str, Any] | None = None) -> tuple[int, dict[str, Any]]:
    data = None
    headers = {}

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["content-type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            raw = response.read()
            try:
                body = json.loads(raw.decode("utf-8"))
            except Exception:
                body = {
                    "ok": True,
                    "non_json_response": True,
                    "bytes": len(raw),
                    "content_type": response.headers.get("content-type"),
                }
            return response.status, body
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            body = json.loads(raw.decode("utf-8"))
        except Exception:
            body = {"ok": False, "error": raw.decode("utf-8", errors="replace")}
        return exc.code, body


def main() -> int:
    parser = argparse.ArgumentParser(description="AION O21 local voice smoke test")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--text", default="Hello, this is AION local voice.")
    args = parser.parse_args()

    base = args.base_url.rstrip("/")

    checks: list[dict[str, Any]] = []

    status_code, providers = request_json("GET", f"{base}/api/aion/voice/providers")
    checks.append(
        {
            "name": "provider_status",
            "status_code": status_code,
            "ok": status_code == 200 and providers.get("tts_provider") == "kokoro",
            "response": providers,
        }
    )

    status_code, tts = request_json(
        "POST",
        f"{base}/api/aion/voice/tts",
        {
            "text": args.text,
            "provider": "kokoro",
            "voice_id": "af_heart",
        },
    )

    # Before Kokoro deps are installed, this may return local_tts_error.
    # After deps are installed, this may return non-json audio bytes.
    tts_ok = (
        status_code == 200
        and (
            tts.get("non_json_response") is True
            or tts.get("provider") == "kokoro"
        )
        and tts.get("provider") != "elevenlabs"
    )

    checks.append(
        {
            "name": "tts_kokoro_route",
            "status_code": status_code,
            "ok": tts_ok,
            "response": tts,
        }
    )

    print(json.dumps({"ok": all(item["ok"] for item in checks), "checks": checks}, indent=2))

    return 0 if all(item["ok"] for item in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
