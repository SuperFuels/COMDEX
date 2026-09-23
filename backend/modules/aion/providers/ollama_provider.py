from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests


DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_OLLAMA_MODEL = "gemma4:e2b"
DEFAULT_TIMEOUT_SECONDS = 120


class OllamaProviderError(RuntimeError):
    pass


@dataclass(slots=True)
class OllamaGenerateResult:
    model: str
    response: str
    done: bool
    done_reason: Optional[str]
    raw: Dict[str, Any]


class OllamaProvider:
    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL") or DEFAULT_OLLAMA_BASE_URL).rstrip("/")
        self.model = model or os.getenv("OLLAMA_MODEL") or DEFAULT_OLLAMA_MODEL
        self.timeout_seconds = timeout_seconds

    def health(self) -> Dict[str, Any]:
        url = f"{self.base_url}/api/tags"
        try:
            response = requests.get(url, timeout=self.timeout_seconds)
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            raise OllamaProviderError(f"Failed to reach Ollama at {url}: {exc}") from exc

        return payload

    def generate(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        model: Optional[str] = None,
        stream: bool = False,
        options: Optional[Dict[str, Any]] = None,
        think: Optional[bool] = None,
    ) -> OllamaGenerateResult:
        resolved_model = model or self.model
        url = f"{self.base_url}/api/generate"

        payload: Dict[str, Any] = {
            "model": resolved_model,
            "prompt": prompt,
            "stream": stream,
        }

        if system:
            payload["system"] = system

        if options:
            payload["options"] = options
        if think is not None:
            payload["think"] = think

        try:
            response = requests.post(url, json=payload, timeout=self.timeout_seconds)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as exc:
            raise OllamaProviderError(
                f"Failed Ollama generate request for model '{resolved_model}': {exc}"
            ) from exc
        except ValueError as exc:
            raise OllamaProviderError("Ollama returned non-JSON response") from exc

        return OllamaGenerateResult(
            model=data.get("model", resolved_model),
            response=data.get("response", ""),
            done=bool(data.get("done", False)),
            done_reason=data.get("done_reason"),
            raw=data,
        )
