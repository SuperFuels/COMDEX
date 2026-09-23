"""Phase 0 truth baseline for the Glyph-addressed adaptive runtime.

Runtime-provided values are recorded as measurements. Unsupported values remain
explicitly unavailable so later optimisation claims cannot compare against guesses.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Iterable, Mapping, Optional, Protocol

import requests


DEFAULT_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_WORKLOAD_PATH = Path(__file__).with_name("workloads.v1.json")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(value: str | bytes) -> str:
    raw = value.encode("utf-8") if isinstance(value, str) else value
    return hashlib.sha256(raw).hexdigest()


def _command(args: list[str]) -> Optional[str]:
    try:
        completed = subprocess.run(
            args, check=True, capture_output=True, text=True, timeout=10
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return completed.stdout.strip() or completed.stderr.strip() or None


@dataclass(frozen=True)
class Measurement:
    value: Optional[float | int | str]
    unit: str
    status: str
    source: str
    note: str = ""


def _measured(value: float | int | str, unit: str, source: str) -> Measurement:
    return Measurement(value=value, unit=unit, status="measured", source=source)


def _unavailable(unit: str, source: str, note: str) -> Measurement:
    return Measurement(value=None, unit=unit, status="unavailable", source=source, note=note)


@dataclass(frozen=True)
class WorkloadCase:
    case_id: str
    category: str
    prompt: str
    quality_check: Mapping[str, Any]
    max_output_tokens: int = 128
    temperature: float = 0.0

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "WorkloadCase":
        return cls(
            case_id=str(value["case_id"]),
            category=str(value["category"]),
            prompt=str(value["prompt"]),
            quality_check=dict(value.get("quality_check") or {"type": "human_review"}),
            max_output_tokens=int(value.get("max_output_tokens", 128)),
            temperature=float(value.get("temperature", 0.0)),
        )


@dataclass(frozen=True)
class StreamGeneration:
    text: str
    first_token_seconds: Optional[float]
    wall_seconds: float
    final_event: Mapping[str, Any]


class StreamingClient(Protocol):
    def generate(self, *, model: str, case: WorkloadCase) -> StreamGeneration: ...


class OllamaStreamingClient:
    """Streaming Ollama adapter with observable first-token timing."""

    def __init__(self, base_url: str = DEFAULT_BASE_URL, timeout_seconds: int = 300) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def tags(self) -> Mapping[str, Any]:
        response = requests.get(f"{self.base_url}/api/tags", timeout=10)
        response.raise_for_status()
        return response.json()

    def generate(self, *, model: str, case: WorkloadCase) -> StreamGeneration:
        started = time.perf_counter()
        first_token: Optional[float] = None
        chunks: list[str] = []
        final_event: dict[str, Any] = {}
        response = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": model,
                "prompt": case.prompt,
                "stream": True,
                "think": False,
                "keep_alive": "5m",
                "options": {
                    "temperature": case.temperature,
                    "num_predict": case.max_output_tokens,
                    "seed": 0,
                },
            },
            stream=True,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        for raw_line in response.iter_lines():
            if not raw_line:
                continue
            event = json.loads(raw_line.decode("utf-8"))
            chunk = str(event.get("response") or "")
            if chunk:
                if first_token is None:
                    first_token = time.perf_counter() - started
                chunks.append(chunk)
            if event.get("done"):
                final_event = event
        return StreamGeneration(
            text="".join(chunks),
            first_token_seconds=first_token,
            wall_seconds=time.perf_counter() - started,
            final_event=final_event,
        )


@dataclass(frozen=True)
class BenchmarkResult:
    case_id: str
    category: str
    model: str
    response: str
    response_sha256: str
    quality_status: str
    quality_detail: str
    measurements: Mapping[str, Measurement]
    runtime_evidence: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BenchmarkReport:
    schema_version: str
    run_id: str
    started_at: str
    completed_at: str
    model: str
    runtime: str
    workload_manifest_sha256: str
    machine: Mapping[str, Any]
    results: list[BenchmarkResult]
    reproducibility: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_workloads(path: Path = DEFAULT_WORKLOAD_PATH) -> list[WorkloadCase]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = [WorkloadCase.from_dict(item) for item in payload["cases"]]
    ids = [case.case_id for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("Workload case_id values must be unique")
    return cases


def _sysctl(name: str) -> Optional[str]:
    return _command(["sysctl", "-n", name])


def _runtime_version(executable: str, args: list[str]) -> Optional[str]:
    path = shutil.which(executable)
    return _command([path, *args]) if path else None


def _storage_inventory(path: Path) -> Mapping[str, Any]:
    resolved = path.expanduser().resolve()
    if not resolved.exists():
        return {"path": str(resolved), "available": False}
    stat = os.statvfs(resolved)
    return {
        "path": str(resolved),
        "available": True,
        "capacity_bytes": stat.f_blocks * stat.f_frsize,
        "available_bytes": stat.f_bavail * stat.f_frsize,
    }


def benchmark_storage(path: Path, probe_bytes: int = 64 * 1024 * 1024) -> Mapping[str, Any]:
    """Run a bounded sequential storage probe and remove its temporary file."""
    root = path.expanduser().resolve()
    if probe_bytes <= 0:
        raise ValueError("probe_bytes must be positive")
    root.mkdir(parents=True, exist_ok=True)
    block = hashlib.sha256(b"aion-inference-storage-probe-v1").digest() * 32_768
    remaining = probe_bytes
    probe_path: Optional[Path] = None
    try:
        descriptor, raw_path = tempfile.mkstemp(prefix=".aion-storage-probe-", dir=root)
        probe_path = Path(raw_path)
        write_started = time.perf_counter()
        with os.fdopen(descriptor, "wb", buffering=0) as handle:
            while remaining:
                payload = block[: min(len(block), remaining)]
                handle.write(payload)
                remaining -= len(payload)
            os.fsync(handle.fileno())
        write_seconds = time.perf_counter() - write_started

        digest = hashlib.sha256()
        read_started = time.perf_counter()
        with probe_path.open("rb", buffering=0) as handle:
            if sys.platform == "darwin":
                try:
                    import fcntl

                    fcntl.fcntl(handle.fileno(), 48, 1)  # F_NOCACHE
                except (ImportError, OSError):
                    pass
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
        read_seconds = time.perf_counter() - read_started
        mib = probe_bytes / (1024 * 1024)
        return {
            "status": "measured",
            "method": "bounded_sequential_write_fsync_then_uncached_read",
            "probe_bytes": probe_bytes,
            "write_seconds": write_seconds,
            "write_mib_per_second": mib / write_seconds,
            "read_seconds": read_seconds,
            "read_mib_per_second": mib / read_seconds,
            "content_sha256": digest.hexdigest(),
            "temporary_file_removed": True,
        }
    finally:
        if probe_path is not None:
            probe_path.unlink(missing_ok=True)


def collect_machine_inventory(
    storage_root: Optional[Path] = None, *, probe_storage: bool = False
) -> dict[str, Any]:
    """Collect stable, non-secret facts needed to reproduce a benchmark."""
    memory_bytes = _sysctl("hw.memsize")
    gpu_cores = None
    hardware_json = _command(
        ["system_profiler", "SPHardwareDataType", "SPDisplaysDataType", "-json"]
    )
    hardware: dict[str, Any] = {}
    if hardware_json:
        try:
            parsed = json.loads(hardware_json)
            hw = (parsed.get("SPHardwareDataType") or [{}])[0]
            display = (parsed.get("SPDisplaysDataType") or [{}])[0]
            hardware = {
                "machine_name": hw.get("machine_name"),
                "machine_model": hw.get("machine_model"),
                "chip": hw.get("chip_type"),
                "cpu_topology": hw.get("number_processors"),
                "physical_memory_label": hw.get("physical_memory"),
            }
            gpu_cores = display.get("sppci_cores")
        except (ValueError, TypeError, IndexError):
            hardware = {}

    storage = _storage_inventory(storage_root) if storage_root else None
    if storage is not None and probe_storage and storage.get("available"):
        storage = {**storage, "throughput_probe": benchmark_storage(storage_root)}
    return {
        "captured_at": _utc_now(),
        "platform": platform.platform(),
        "architecture": platform.machine(),
        "python": platform.python_version(),
        "hardware": hardware,
        "memory_bytes": int(memory_bytes) if memory_bytes and memory_bytes.isdigit() else None,
        "gpu_cores": int(gpu_cores) if str(gpu_cores).isdigit() else None,
        "runtime_storage": storage,
        "runtimes": {
            "ollama": _runtime_version("ollama", ["--version"]),
            "mlx_lm": _runtime_version("mlx_lm.generate", ["--help"]),
            "llama_cpp": _runtime_version("llama-cli", ["--version"]),
            "airllm": _command([sys.executable, "-c", "import airllm; print(airllm.__version__)"]),
        },
    }


def collect_model_store_evidence(model_store: Path, model: str) -> Mapping[str, Any]:
    """Prove that an Ollama model manifest is present under a chosen store."""
    root = model_store.expanduser().resolve()
    name, _, tag = model.partition(":")
    tag = tag or "latest"
    manifest = root / "manifests" / "registry.ollama.ai" / "library" / name / tag
    evidence: dict[str, Any] = {
        "path": str(root),
        "model": model,
        "manifest_path": str(manifest),
        "manifest_available": manifest.is_file(),
    }
    if manifest.is_file():
        raw = manifest.read_bytes()
        evidence["manifest_sha256"] = _sha256(raw)
        try:
            payload = json.loads(raw)
            layers = payload.get("layers") or []
            evidence["declared_layer_bytes"] = sum(
                int(layer.get("size") or 0) for layer in layers if isinstance(layer, dict)
            )
            evidence["declared_layer_count"] = len(layers)
        except (TypeError, ValueError):
            evidence["manifest_parse_error"] = True
    return evidence


def _quality(response: str, check: Mapping[str, Any]) -> tuple[str, str]:
    check_type = str(check.get("type") or "human_review")
    if check_type == "contains_all":
        expected = [str(item).casefold() for item in check.get("values") or []]
        missing = [item for item in expected if item not in response.casefold()]
        return ("pass", "all required values present") if not missing else ("fail", f"missing: {missing}")
    if check_type == "regex":
        pattern = str(check.get("pattern") or "")
        return ("pass", "pattern matched") if re.search(pattern, response, re.I | re.S) else ("fail", "pattern did not match")
    return "needs_human_review", "no deterministic quality oracle for this case"


def _duration_seconds(event: Mapping[str, Any], key: str) -> Optional[float]:
    value = event.get(key)
    return float(value) / 1_000_000_000 if isinstance(value, (int, float)) else None


def _measurements(generation: StreamGeneration) -> dict[str, Measurement]:
    event = generation.final_event
    prompt_count = event.get("prompt_eval_count")
    output_count = event.get("eval_count")
    eval_seconds = _duration_seconds(event, "eval_duration")
    tokens_per_second = (
        float(output_count) / eval_seconds
        if isinstance(output_count, int) and eval_seconds and eval_seconds > 0
        else None
    )
    load_seconds = _duration_seconds(event, "load_duration")
    prompt_seconds = _duration_seconds(event, "prompt_eval_duration")
    return {
        "time_to_first_token": _measured(generation.first_token_seconds, "seconds", "client_stream_clock") if generation.first_token_seconds is not None else _unavailable("seconds", "client_stream_clock", "runtime emitted no response token"),
        "wall_time": _measured(generation.wall_seconds, "seconds", "client_monotonic_clock"),
        "prompt_tokens": _measured(prompt_count, "tokens", "ollama_final_event") if isinstance(prompt_count, int) else _unavailable("tokens", "ollama_final_event", "prompt_eval_count absent"),
        "output_tokens": _measured(output_count, "tokens", "ollama_final_event") if isinstance(output_count, int) else _unavailable("tokens", "ollama_final_event", "eval_count absent"),
        "tokens_per_second": _measured(tokens_per_second, "tokens/second", "ollama_eval_count_and_duration") if tokens_per_second is not None else _unavailable("tokens/second", "ollama_final_event", "token count or duration absent"),
        "load_time": _measured(load_seconds, "seconds", "ollama_final_event") if load_seconds is not None else _unavailable("seconds", "ollama_final_event", "load_duration absent"),
        "prompt_evaluation_time": _measured(prompt_seconds, "seconds", "ollama_final_event") if prompt_seconds is not None else _unavailable("seconds", "ollama_final_event", "prompt_eval_duration absent"),
        "peak_unified_memory": _unavailable("bytes", "ollama_api", "Ollama does not expose per-request unified-memory peak"),
        "ssd_bytes_read": _unavailable("bytes", "ollama_api", "No attributable per-request storage counter is exposed"),
        "model_weight_bytes_moved": _unavailable("bytes", "ollama_api", "Weight traffic is not exposed by this runtime"),
        "kv_cache_size": _unavailable("bytes", "ollama_api", "KV cache size is not exposed by this runtime"),
        "energy": _unavailable("joules", "host", "No calibrated per-request energy sensor is available"),
        "expert_activations": _unavailable("count", "ollama_api", "Expert routing telemetry is not exposed"),
    }


def run_baseline(
    *,
    model: str,
    cases: Iterable[WorkloadCase],
    client: StreamingClient,
    machine: Optional[Mapping[str, Any]] = None,
    workload_manifest_bytes: Optional[bytes] = None,
) -> BenchmarkReport:
    started_at = _utc_now()
    case_list = list(cases)
    results: list[BenchmarkResult] = []
    for case in case_list:
        generation = client.generate(model=model, case=case)
        quality_status, quality_detail = _quality(generation.text, case.quality_check)
        results.append(BenchmarkResult(
            case_id=case.case_id,
            category=case.category,
            model=model,
            response=generation.text,
            response_sha256=_sha256(generation.text),
            quality_status=quality_status,
            quality_detail=quality_detail,
            measurements=_measurements(generation),
            runtime_evidence={key: generation.final_event.get(key) for key in (
                "model", "created_at", "done", "done_reason", "total_duration",
                "load_duration", "prompt_eval_count", "prompt_eval_duration",
                "eval_count", "eval_duration",
            ) if key in generation.final_event},
        ))

    canonical_cases = json.dumps([asdict(case) for case in case_list], sort_keys=True).encode()
    manifest_hash = _sha256(workload_manifest_bytes or canonical_cases)
    run_material = json.dumps({
        "model": model,
        "manifest": manifest_hash,
        "responses": [result.response_sha256 for result in results],
    }, sort_keys=True)
    return BenchmarkReport(
        schema_version="aion.inference.baseline.v1",
        run_id=f"baseline-{_sha256(run_material)[:16]}",
        started_at=started_at,
        completed_at=_utc_now(),
        model=model,
        runtime="ollama_streaming_api",
        workload_manifest_sha256=manifest_hash,
        machine=dict(machine or collect_machine_inventory()),
        results=results,
        reproducibility={
            "temperature": "defined per workload",
            "seed": 0,
            "streaming": True,
            "thinking": False,
            "unsupported_metrics_are_nullable": True,
            "response_hashes_recorded": True,
        },
    )
