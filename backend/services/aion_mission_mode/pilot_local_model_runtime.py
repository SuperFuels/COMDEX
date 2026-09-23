"""Loopback-only local runtime for a Pilot Model Harness.

This is bounded transport and loopback runtime startup. AION selects the model
profile and Pilot; no provider fallback, tool execution or business-memory
mutation occurs here.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
from time import monotonic
from time import sleep
from typing import Any, Callable, Mapping
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .pilot_model_harness import (
    GPT_OSS_HARMONY_ADAPTER,
    PilotModelHarnessError,
    create_harness_receipt,
    parse_gpt_oss_proposal,
)


GPT_OSS_20B_Q4_MODEL_ID = "openai-gpt-oss-20b-q4-k-m"
QWEN3_8B_FAST_LOCAL_MODEL_ID = "qwen3-8b-fast-local-q4"
OPENAI_COMPATIBLE_BOUNDED_CHAT_ADAPTER = "openai_compatible_bounded_chat.v1"


class LocalModelRuntimeError(RuntimeError):
    pass


def selected_local_runtime_profile(
    *, model_id: str, adapter: str, endpoint: str, model_sha256: str,
    model_path: str = "",
    finance_arithmetic: str, chat_template_kwargs: Any = None,
    max_output_tokens: Any = None, context_size: Any = None,
    parallel_slots: Any = None,
) -> dict[str, Any]:
    """Validate a selectable Vault package without coupling Pilot to a model name."""
    digest = str(model_sha256 or "").lower()
    if not str(model_id or "").strip():
        raise LocalModelRuntimeError("selected_local_model_id_required")
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise LocalModelRuntimeError("selected_local_model_sha256_required")
    if adapter != OPENAI_COMPATIBLE_BOUNDED_CHAT_ADAPTER:
        raise LocalModelRuntimeError("selected_local_model_adapter_not_supported")
    if finance_arithmetic != "verified_tessaris_tools_required":
        raise LocalModelRuntimeError("verified_finance_arithmetic_boundary_required")
    template_kwargs = dict(chat_template_kwargs) if isinstance(chat_template_kwargs, Mapping) else {}
    tokens = max(64, min(int(max_output_tokens or 320), 2_048))
    context = max(4_096, min(int(context_size or 4_096), 8_192))
    slots = max(1, min(int(parallel_slots or 1), 2))
    path = Path(str(model_path or "")).resolve() if model_path else None
    if path is not None and not path.is_file():
        raise LocalModelRuntimeError("selected_local_model_file_missing")
    return {
        "schema_version": "aion.pilot_local_model_runtime.v1",
        "model_id": str(model_id), "adapter": adapter,
        "endpoint": _loopback_endpoint(endpoint), "model_sha256": digest,
        "model_path": str(path) if path is not None else "",
        "allow_network_fallback": False, "allows_tool_execution": False,
        "allows_memory_mutation": False,
        "finance_arithmetic": "verified_tessaris_tools_required",
        "chat_template_kwargs": template_kwargs, "max_output_tokens": tokens,
        "context_size": context, "parallel_slots": slots,
    }


def qwen3_fast_local_runtime_profile(*, endpoint: str, model_sha256: str) -> dict[str, Any]:
    digest = str(model_sha256 or "").lower()
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise LocalModelRuntimeError("qwen_model_sha256_required")
    return {
        "schema_version": "aion.pilot_local_model_runtime.v1",
        "model_id": QWEN3_8B_FAST_LOCAL_MODEL_ID,
        "adapter": OPENAI_COMPATIBLE_BOUNDED_CHAT_ADAPTER,
        "endpoint": _loopback_endpoint(endpoint),
        "model_sha256": digest,
        "allow_network_fallback": False,
        "allows_tool_execution": False,
        "allows_memory_mutation": False,
        "finance_arithmetic": "verified_tessaris_tools_required",
        "chat_template_kwargs": {"enable_thinking": False},
        "max_output_tokens": 320,
    }


def _loopback_endpoint(endpoint: str) -> str:
    parsed = urlparse(str(endpoint or ""))
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise LocalModelRuntimeError("local_runtime_endpoint_must_be_loopback_http")
    if not parsed.port:
        raise LocalModelRuntimeError("local_runtime_endpoint_port_required")
    return f"http://{parsed.hostname}:{parsed.port}"


def gpt_oss_local_runtime_profile(*, endpoint: str, model_sha256: str) -> dict[str, Any]:
    """Create the explicit runtime identity required before a harness may call it."""
    digest = str(model_sha256 or "").lower()
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise LocalModelRuntimeError("gpt_oss_model_sha256_required")
    return {
        "schema_version": "aion.pilot_local_model_runtime.v1",
        "model_id": GPT_OSS_20B_Q4_MODEL_ID,
        "adapter": GPT_OSS_HARMONY_ADAPTER,
        "endpoint": _loopback_endpoint(endpoint),
        "model_sha256": digest,
        "allow_network_fallback": False,
        "allows_tool_execution": False,
        "allows_memory_mutation": False,
    }


def _http_chat_completion(endpoint: str, body: Mapping[str, Any], timeout_seconds: float) -> dict[str, Any]:
    request = Request(
        f"{endpoint}/v1/chat/completions",
        data=json.dumps(body, separators=(",", ":")).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # nosec B310: endpoint is loopback validated
            return json.loads(response.read().decode("utf-8"))
    except (URLError, OSError, json.JSONDecodeError) as exc:
        raise LocalModelRuntimeError("local_model_runtime_unavailable") from exc


_SERVER_LOCK = threading.RLock()
_SERVER_PROCESS: subprocess.Popen[Any] | None = None


def _runtime_ready(endpoint: str, timeout_seconds: float = 1.0) -> bool:
    try:
        with urlopen(Request(f"{endpoint}/health", method="GET"), timeout=timeout_seconds) as response:  # nosec B310
            return 200 <= int(response.status) < 500
    except (URLError, OSError):
        return False


def _runtime_matches_profile(endpoint: str, runtime_profile: Mapping[str, Any]) -> bool:
    """Do not reuse a healthy server whose context was divided too aggressively."""
    try:
        with urlopen(Request(f"{endpoint}/props", method="GET"), timeout=2.0) as response:  # nosec B310
            props = json.loads(response.read().decode("utf-8"))
    except (URLError, OSError, json.JSONDecodeError):
        return False
    settings = props.get("default_generation_settings")
    reported_context = props.get("n_ctx")
    if not reported_context and isinstance(settings, Mapping):
        reported_context = settings.get("n_ctx")
    desired_context = int(runtime_profile.get("context_size") or 4_096)
    desired_slots = int(runtime_profile.get("parallel_slots") or 1)
    return int(reported_context or 0) >= desired_context and int(props.get("total_slots") or 0) == desired_slots


def ensure_selected_local_runtime(runtime_profile: Mapping[str, Any]) -> dict[str, Any]:
    """Start the approved llama.cpp server on loopback when it is not already ready."""
    global _SERVER_PROCESS
    endpoint = _loopback_endpoint(str(runtime_profile.get("endpoint") or ""))
    if _runtime_ready(endpoint) and _runtime_matches_profile(endpoint, runtime_profile):
        return {"status": "ready", "endpoint": endpoint, "started": False}
    parsed = urlparse(endpoint)
    model_path = Path(str(runtime_profile.get("model_path") or "")).resolve()
    if not model_path.is_file():
        raise LocalModelRuntimeError("selected_local_model_file_missing")
    expected_hash = str(runtime_profile.get("model_sha256") or "").lower()
    server = shutil.which("llama-server")
    if not server:
        raise LocalModelRuntimeError("llama_server_not_installed")
    with _SERVER_LOCK:
        if _runtime_ready(endpoint) and _runtime_matches_profile(endpoint, runtime_profile):
            return {"status": "ready", "endpoint": endpoint, "started": False}
        if _SERVER_PROCESS is not None and _SERVER_PROCESS.poll() is None:
            _SERVER_PROCESS.terminate()
        runtime_dir = Path(os.environ.get("TESSARIS_DATA_ROOT") or ".runtime/AION_BUSINESS") / "local_model_runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        log_path = runtime_dir / "qwen3-8b-fast-local.log"
        log_handle = log_path.open("ab")
        command = [
            server, "--model", str(model_path), "--host", "127.0.0.1",
            "--port", str(parsed.port),
            "--ctx-size", str(int(runtime_profile.get("context_size") or 4_096)),
            "--parallel", str(int(runtime_profile.get("parallel_slots") or 1)),
            "--threads", "6",
            "--jinja", "--alias", str(runtime_profile.get("model_id") or "local-model"),
        ]
        _SERVER_PROCESS = subprocess.Popen(  # noqa: S603 - executable resolved by shutil.which
            command, stdout=log_handle, stderr=subprocess.STDOUT, start_new_session=True,
        )
        log_handle.close()
    # Loading 5 GB directly from removable media can take several minutes on a
    # cold start. Keep the wait bounded, but long enough for the verified card.
    deadline = monotonic() + 300.0
    while monotonic() < deadline:
        if _runtime_ready(endpoint, 2.0) and _runtime_matches_profile(endpoint, runtime_profile):
            return {
                "status": "ready", "endpoint": endpoint, "started": True,
                "pid": _SERVER_PROCESS.pid, "model_sha256": expected_hash,
            }
        if _SERVER_PROCESS.poll() is not None:
            raise LocalModelRuntimeError("local_model_server_start_failed")
        sleep(0.5)
    raise LocalModelRuntimeError("local_model_server_start_timeout")


def _response_text(response: Mapping[str, Any]) -> str:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], Mapping):
        raise LocalModelRuntimeError("local_runtime_response_missing_choice")
    message = choices[0].get("message")
    if not isinstance(message, Mapping):
        raise LocalModelRuntimeError("local_runtime_response_missing_message")
    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return content
    # Some OpenAI-compatible local servers normalise Harmony calls into this form.
    calls = message.get("tool_calls")
    if isinstance(calls, list) and len(calls) == 1 and isinstance(calls[0], Mapping):
        function = calls[0].get("function", {})
        if isinstance(function, Mapping):
            arguments = function.get("arguments", "{}")
            try:
                decoded = json.loads(arguments) if isinstance(arguments, str) else arguments
            except json.JSONDecodeError as exc:
                raise LocalModelRuntimeError("local_runtime_tool_arguments_invalid_json") from exc
            return "<|call|>" + json.dumps({"name": function.get("name"), "arguments": decoded}) + "<|end|>"
    raise LocalModelRuntimeError("local_runtime_response_empty")


def run_gpt_oss_harness_locally(
    *,
    contract: Mapping[str, Any],
    runtime_profile: Mapping[str, Any],
    transport: Callable[[str, Mapping[str, Any], float], dict[str, Any]] = _http_chat_completion,
) -> dict[str, Any]:
    """Call an already-running local GPT-OSS server and return only a proposal + receipt."""
    if contract.get("adapter") != GPT_OSS_HARMONY_ADAPTER:
        raise PilotModelHarnessError("contract_is_not_gpt_oss_harmony")
    if runtime_profile.get("model_id") != GPT_OSS_20B_Q4_MODEL_ID:
        raise LocalModelRuntimeError("runtime_profile_model_not_permitted")
    if runtime_profile.get("adapter") != GPT_OSS_HARMONY_ADAPTER:
        raise LocalModelRuntimeError("runtime_profile_adapter_mismatch")
    if runtime_profile.get("allow_network_fallback") is not False:
        raise LocalModelRuntimeError("network_fallback_must_be_disabled")
    if runtime_profile.get("allows_tool_execution") is not False:
        raise LocalModelRuntimeError("runtime_may_not_execute_tools")
    endpoint = _loopback_endpoint(str(runtime_profile.get("endpoint") or ""))
    request = {
        "model": GPT_OSS_20B_Q4_MODEL_ID,
        "messages": contract["adapter_request"]["messages"],
        "max_tokens": contract["limits"]["max_output_tokens"],
        "temperature": 0,
        "stream": False,
    }
    start = monotonic()
    response = transport(endpoint, request, float(contract["limits"]["max_latency_ms"]) / 1000)
    elapsed_ms = round((monotonic() - start) * 1000)
    event = parse_gpt_oss_proposal(contract=contract, model_text=_response_text(response))
    receipt = create_harness_receipt(contract=contract, event=event, elapsed_ms=elapsed_ms)
    return {
        "schema_version": "aion.pilot_local_model_harness_run.v1",
        "runtime_profile": {
            "model_id": runtime_profile["model_id"],
            "model_sha256": runtime_profile["model_sha256"],
            "endpoint": endpoint,
            "allow_network_fallback": False,
        },
        "event": event,
        "receipt": receipt,
        "tool_executed": False,
        "external_side_effect_executed": False,
        "memory_mutated": False,
    }


def run_selected_local_chat(
    *, prompt: str, runtime_profile: Mapping[str, Any],
    transport: Callable[[str, Mapping[str, Any], float], dict[str, Any]] = _http_chat_completion,
) -> dict[str, Any]:
    """Run whichever accepted OpenAI-compatible local model the Vault selected."""
    model_id = str(runtime_profile.get("model_id") or "")
    if not model_id:
        raise LocalModelRuntimeError("runtime_profile_model_not_permitted")
    if runtime_profile.get("adapter") != OPENAI_COMPATIBLE_BOUNDED_CHAT_ADAPTER:
        raise LocalModelRuntimeError("runtime_profile_adapter_mismatch")
    if runtime_profile.get("allow_network_fallback") is not False:
        raise LocalModelRuntimeError("network_fallback_must_be_disabled")
    if runtime_profile.get("allows_tool_execution") is not False:
        raise LocalModelRuntimeError("runtime_may_not_execute_tools")
    if runtime_profile.get("finance_arithmetic") != "verified_tessaris_tools_required":
        raise LocalModelRuntimeError("verified_finance_arithmetic_boundary_required")
    endpoint = _loopback_endpoint(str(runtime_profile.get("endpoint") or ""))
    if transport is _http_chat_completion:
        ensure_selected_local_runtime(runtime_profile)
    body = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": "Return only the requested JSON. Do not show hidden reasoning. Never execute tools or calculate Finance figures; use supplied verified facts."},
            {"role": "user", "content": str(prompt)},
        ],
        "max_tokens": int(runtime_profile.get("max_output_tokens") or 320),
        "temperature": 0, "stream": False,
    }
    template_kwargs = runtime_profile.get("chat_template_kwargs")
    if isinstance(template_kwargs, Mapping) and template_kwargs:
        body["chat_template_kwargs"] = dict(template_kwargs)
    response = transport(endpoint, body, 180.0)
    return {"content": _response_text(response), "provider": "local_model", "model": model_id}


def run_qwen3_bounded_chat_locally(*, prompt: str, runtime_profile: Mapping[str, Any]) -> dict[str, Any]:
    """Backward-compatible alias; selection is now Vault/profile driven."""
    return run_selected_local_chat(prompt=prompt, runtime_profile=runtime_profile)
