from __future__ import annotations

import json
import os
import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def http_get(base_url: str, path: str, timeout: int = 30):
    try:
        with urllib.request.urlopen(base_url + path, timeout=timeout) as response:
            return response.status, response.read(), dict(response.headers)
    except urllib.error.HTTPError as exc:
        body = exc.read()
        raise RuntimeError(
            f"GET {path} failed with HTTP {exc.code}: {body[:1200]!r}"
        ) from exc


def http_post_json(base_url: str, path: str, payload: dict):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        base_url + path,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=240) as response:
            return response.status, response.read(), dict(response.headers)
    except urllib.error.HTTPError as exc:
        body = exc.read()
        raise RuntimeError(
            f"POST JSON {path} failed with HTTP {exc.code}: {body[:1200]!r}"
        ) from exc


def http_post_multipart_file(base_url: str, path: str, field_name: str, file_path: Path):
    boundary = "----AIONO22EVoiceBoundary"
    file_bytes = file_path.read_bytes()
    body = b"".join([
        f"--{boundary}\r\n".encode(),
        f'Content-Disposition: form-data; name="{field_name}"; filename="{file_path.name}"\r\n'.encode(),
        b"Content-Type: audio/wav\r\n\r\n",
        file_bytes,
        b"\r\n",
        f"--{boundary}--\r\n".encode(),
    ])
    req = urllib.request.Request(
        base_url + path,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=240) as response:
            return response.status, response.read(), dict(response.headers)
    except urllib.error.HTTPError as exc:
        body = exc.read()
        raise RuntimeError(
            f"POST multipart {path} failed with HTTP {exc.code}: {body[:1200]!r}"
        ) from exc


def wait_for_openapi(proc, base_url: str, timeout_seconds: int = 120) -> dict:
    started = time.time()
    last_error = None

    while time.time() - started < timeout_seconds:
        if proc.poll() is not None:
            stdout, stderr = proc.communicate(timeout=3)
            raise RuntimeError(
                f"Backend exited early with code {proc.returncode}\nSTDOUT:\n{stdout[-4000:]}\nSTDERR:\n{stderr[-4000:]}"
            )

        try:
            status, body, _ = http_get(base_url, "/openapi.json", timeout=10)
            if status == 200:
                return json.loads(body.decode("utf-8"))
        except Exception as exc:
            last_error = exc
            time.sleep(1)

    raise RuntimeError(f"Backend did not expose OpenAPI at {base_url}/openapi.json: {last_error!r}")


def discover_voice_paths(openapi: dict) -> dict:
    paths = openapi.get("paths") or {}
    voice_paths = sorted(path for path in paths if "voice" in path)

    def has_method(path: str, method: str) -> bool:
        return method.lower() in (paths.get(path) or {})

    def pick(method: str, suffix: str) -> str:
        candidates = [
            path for path in voice_paths
            if path.endswith(suffix) and has_method(path, method)
        ]
        if not candidates:
            raise RuntimeError(
                json.dumps(
                    {
                        "error": f"No live OpenAPI voice route for {method} {suffix}",
                        "voice_paths": voice_paths,
                    },
                    indent=2,
                )
            )
        # Prefer the shortest exact-looking path if duplicate/legacy routes exist.
        return sorted(candidates, key=len)[0]

    return {
        "providers": pick("GET", "/providers"),
        "tts": pick("POST", "/tts"),
        "stt": pick("POST", "/stt"),
        "voice_paths": voice_paths,
    }


def main() -> int:
    out_dir = Path(".runtime/voice_runtime_tests/o22e")
    out_dir.mkdir(parents=True, exist_ok=True)

    wav_path = out_dir / "endpoint_worker_tts.wav"
    manifest_path = out_dir / "endpoint_worker_manifest.json"
    diagnostics_path = out_dir / "endpoint_worker_diagnostics.json"

    port = find_free_port()
    base_url = f"http://127.0.0.1:{port}"

    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    env["AION_VOICE_WORKER_ENABLED"] = "true"
    env.setdefault("AION_TTS_PROVIDER", "kokoro")
    env.setdefault("AION_STT_PROVIDER", "faster_whisper")
    env.setdefault("AION_ALLOW_ELEVENLABS", "false")
    env.setdefault("AION_ALLOW_BROWSER_SPEECH", "false")

    proc = subprocess.Popen(
        [
            ".venv/bin/python",
            "-m",
            "uvicorn",
            "backend.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        cwd=".",
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        openapi = wait_for_openapi(proc, base_url)
        discovered = discover_voice_paths(openapi)

        diagnostics_path.write_text(
            json.dumps(
                {
                    "base_url": base_url,
                    "discovered": discovered,
                    "openapi_voice_paths": discovered["voice_paths"],
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        provider_status, provider_body, _ = http_get(base_url, discovered["providers"])
        if provider_status != 200:
            raise RuntimeError(f"Providers status was {provider_status}: {provider_body[:300]!r}")

        tts_status, tts_bytes, tts_headers = http_post_json(
            base_url,
            discovered["tts"],
            {
                "text": "AION endpoint worker bridge test. This is a generic runtime check.",
                "provider": "kokoro",
                "voice": "af_heart",
            },
        )

        wav_path.write_bytes(tts_bytes)

        if tts_status != 200:
            raise RuntimeError(f"TTS status was {tts_status}")
        if len(tts_bytes) < 1000:
            raise RuntimeError(f"TTS returned too few bytes: {len(tts_bytes)}")
        if tts_headers.get("x-aion-voice-worker") != "true":
            raise RuntimeError(f"TTS did not use worker bridge: {tts_headers}")

        stt_status, stt_bytes, stt_headers = http_post_multipart_file(
            base_url,
            discovered["stt"],
            "file",
            wav_path,
        )

        if stt_status != 200:
            raise RuntimeError(f"STT status was {stt_status}")
        if stt_headers.get("x-aion-voice-worker") != "true":
            raise RuntimeError(f"STT did not use worker bridge: {stt_headers}")

        stt_payload = json.loads(stt_bytes.decode("utf-8"))

        manifest = {
            "ok": True,
            "phase": "O22E.7",
            "backend": "uvicorn backend.main:app",
            "base_url": base_url,
            "worker_enabled": True,
            "routes": {
                "providers": discovered["providers"],
                "tts": discovered["tts"],
                "stt": discovered["stt"],
            },
            "provider_status": provider_status,
            "tts_status": tts_status,
            "tts_provider": tts_headers.get("x-aion-voice-provider"),
            "tts_worker": tts_headers.get("x-aion-voice-worker"),
            "tts_cloud": tts_headers.get("x-aion-voice-cloud"),
            "wav_path": str(wav_path),
            "wav_size_bytes": len(tts_bytes),
            "stt_status": stt_status,
            "stt_provider": stt_payload.get("provider"),
            "stt_worker": stt_headers.get("x-aion-voice-worker"),
            "transcript": stt_payload.get("text"),
            "business_context_hardcoded": False,
        }

        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(json.dumps(manifest, indent=2))
        return 0

    except Exception as exc:
        stdout = ""
        stderr = ""
        try:
            proc.terminate()
            stdout, stderr = proc.communicate(timeout=10)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

        fail_payload = {
            "ok": False,
            "phase": "O22E.7",
            "base_url": base_url,
            "error": repr(exc),
            "stdout_tail": stdout[-4000:],
            "stderr_tail": stderr[-4000:],
        }
        diagnostics_path.write_text(json.dumps(fail_payload, indent=2), encoding="utf-8")
        print(json.dumps(fail_payload, indent=2))
        return 1

    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except Exception:
                proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
