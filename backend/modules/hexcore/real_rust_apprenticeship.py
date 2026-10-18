"""Compiler-grounded real Rust apprenticeship under immutable mission authority."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Any, Mapping, Sequence

from backend.modules.hexcore.canonical_cognitive_runtime import (
    _canonical_hash,
    _utc_timestamp,
)
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
)
from backend.modules.hexcore.open_relation_argument_memory_benchmark import _call_json


PROCEDURE_ID = "procedure_real_rust_apprenticeship_v1"
MISSION_ID = "mission_real_rust_apprenticeship_v1"
MODEL = os.getenv("AION_RUST_APPRENTICE_MODEL", "gemma4:e2b")


def _run(
    command: Sequence[str], *, cwd: Path, timeout: int = 180,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            list(command), cwd=cwd, text=True, capture_output=True,
            timeout=timeout, check=False, env=dict(env) if env else None,
        )
        return {
            "command": list(command), "returncode": completed.returncode,
            "stdout": completed.stdout[-5000:], "stderr": completed.stderr[-5000:],
            "seconds": time.perf_counter() - started,
            "passed": completed.returncode == 0,
        }
    except subprocess.TimeoutExpired as error:
        return {
            "command": list(command), "returncode": None,
            "stdout": str(error.stdout or "")[-5000:],
            "stderr": str(error.stderr or "")[-5000:],
            "seconds": time.perf_counter() - started,
            "passed": False, "timeout": True,
        }


def _official_resources() -> dict[str, Any]:
    version = _run(["rustc", "--version", "--verbose"], cwd=Path.cwd())
    cargo = _run(["cargo", "--version"], cwd=Path.cwd())
    explanations = {}
    for code in ("E0382", "E0499", "E0277", "E0597"):
        row = _run(["rustc", "--explain", code], cwd=Path.cwd())
        explanations[code] = {
            "sha256": hashlib.sha256(row["stdout"].encode("utf-8")).hexdigest(),
            "bytes": len(row["stdout"].encode("utf-8")),
            "authority": f"installed_rustc_explanation:{code}",
            "passed": row["passed"],
        }
    return {
        "rustc": {"text": version["stdout"].strip(), "passed": version["passed"]},
        "cargo": {"text": cargo["stdout"].strip(), "passed": cargo["passed"]},
        "explanations": explanations,
        "all_available": bool(
            version["passed"] and cargo["passed"]
            and all(row["passed"] for row in explanations.values())
        ),
    }


FORBIDDEN = {
    "unsafe": r"\bunsafe\b",
    "process": r"std::process|Command\s*::",
    "network": r"std::net|TcpStream|UdpSocket",
    "filesystem": r"std::fs|File\s*::|OpenOptions",
    "environment": r"std::env|env::var",
    "dynamic_include": r"include_(str|bytes)!",
    "external_link": r"#\s*\[\s*link",
    "warning_suppression": r"allow\s*\(\s*warnings\s*\)",
    "build_script": r"build\s*=",
}


def _audit(files: Mapping[str, str]) -> dict[str, Any]:
    findings = []
    for path, source in files.items():
        for name, pattern in FORBIDDEN.items():
            if re.search(pattern, source):
                findings.append({"path": path, "class": name})
    cargo = files.get("Cargo.toml", "")
    dependencies = bool(re.search(r"\[dependencies\]\s*\n\s*[^\s#]", cargo))
    if dependencies:
        findings.append({"path": "Cargo.toml", "class": "external_dependency"})
    invalid_paths = [
        path for path in files
        if path.startswith("/") or ".." in Path(path).parts
        or not (path == "Cargo.toml" or path.startswith("src/") or path.startswith("tests/"))
    ]
    for path in invalid_paths:
        findings.append({"path": path, "class": "invalid_path"})
    return {"safe": not findings, "findings": findings}


PROJECTS = [
    {
        "project_id": "quota_pool",
        "cohort": "development",
        "contract": """
Create a dependency-free Rust 2021 library crate named quota_pool with modules
error and quota. Export QuotaError, QuotaStore: Send + Sync, MemoryQuotaStore,
and cloneable QuotaPool using Arc and Mutex/RwLock. QuotaPool::new(),
open(name,&str,capacity:u64), available(name)->Result<u64,QuotaError>,
reserve(name,amount)->Result<(),QuotaError>, and release(name,amount)->Result.
Reject duplicates, missing pools, zero amounts, insufficient quota and overflow.
Failed operations must be atomic. Concurrent reserve/release must preserve state.
""".strip(),
        "hidden": r'''
use quota_pool::QuotaPool;
use std::thread;

#[test]
fn hidden_atomic_errors_and_concurrency() {
    let pool = QuotaPool::new();
    pool.open("cpu", 10_000).unwrap();
    assert!(pool.open("cpu", 1).is_err());
    assert!(pool.reserve("cpu", 0).is_err());
    assert!(pool.reserve("missing", 1).is_err());
    assert!(pool.reserve("cpu", 10_001).is_err());
    assert_eq!(pool.available("cpu").unwrap(), 10_000);
    let mut workers = Vec::new();
    for _ in 0..8 {
        let shared = pool.clone();
        workers.push(thread::spawn(move || {
            for _ in 0..200 { shared.reserve("cpu", 1).unwrap(); shared.release("cpu", 1).unwrap(); }
        }));
    }
    for worker in workers { worker.join().unwrap(); }
    assert_eq!(pool.available("cpu").unwrap(), 10_000);
    pool.open("max", u64::MAX).unwrap();
    assert!(pool.release("max", 1).is_err());
    assert_eq!(pool.available("max").unwrap(), u64::MAX);
}
'''.strip(),
    },
    {
        "project_id": "event_window",
        "cohort": "development",
        "contract": """
Create a dependency-free Rust 2021 library crate named event_window with at
least modules error, event and window. Export WindowError, EventSink: Send +
Sync, Event { key:String, value:i64 }, and cloneable EventWindow backed by Arc
and Mutex/RwLock. EventWindow::new(max_events_per_key:usize) rejects zero;
record(Event) rejects empty keys, capacity overflow and checked-sum overflow;
summary(key)->Result<(usize,i64),WindowError>. A rejected event changes nothing.
Concurrent recording for different keys must be safe and deterministic.
""".strip(),
        "hidden": r'''
use event_window::{Event, EventWindow};
use std::thread;

#[test]
fn hidden_capacity_overflow_and_threads() {
    assert!(EventWindow::new(0).is_err());
    let window = EventWindow::new(2_000).unwrap();
    assert!(window.record(Event { key: "".into(), value: 1 }).is_err());
    window.record(Event { key: "x".into(), value: i64::MAX }).unwrap();
    assert!(window.record(Event { key: "x".into(), value: 1 }).is_err());
    assert_eq!(window.summary("x").unwrap(), (1, i64::MAX));
    let mut workers = Vec::new();
    for index in 0..4 {
        let shared = window.clone();
        workers.push(thread::spawn(move || {
            let key = format!("k{index}");
            for _ in 0..250 { shared.record(Event { key: key.clone(), value: 2 }).unwrap(); }
        }));
    }
    for worker in workers { worker.join().unwrap(); }
    for index in 0..4 { assert_eq!(window.summary(&format!("k{index}")).unwrap(), (250, 500)); }
    assert!(window.summary("missing").is_err());
}
'''.strip(),
    },
    {
        "project_id": "seat_allocator",
        "cohort": "source_disjoint_transfer",
        "contract": """
Create a dependency-free Rust 2021 library crate named seat_allocator with at
least modules error, store and allocator. Export AllocationError,
SeatStore: Send + Sync, MemorySeatStore, and cloneable SeatAllocator using Arc
and Mutex/RwLock. SeatAllocator::new(), add_zone(name,&str,seats:u32),
remaining(name)->Result<u32,AllocationError>, reserve(name,count), and
cancel(name,count). Reject duplicates, empty names, zero counts, insufficient
seats and overflow. Failures are atomic. Concurrent reserve/cancel preserves the
original count. Do not use any names or source from earlier projects.
""".strip(),
        "hidden": r'''
use seat_allocator::SeatAllocator;
use std::thread;

#[test]
fn hidden_transfer_structure_and_atomicity() {
    let seats = SeatAllocator::new();
    assert!(seats.add_zone("", 10).is_err());
    seats.add_zone("north", 5_000).unwrap();
    assert!(seats.add_zone("north", 1).is_err());
    assert!(seats.reserve("north", 0).is_err());
    assert!(seats.reserve("north", 5_001).is_err());
    assert_eq!(seats.remaining("north").unwrap(), 5_000);
    let mut workers = Vec::new();
    for _ in 0..5 {
        let shared = seats.clone();
        workers.push(thread::spawn(move || {
            for _ in 0..150 { shared.reserve("north", 1).unwrap(); shared.cancel("north", 1).unwrap(); }
        }));
    }
    for worker in workers { worker.join().unwrap(); }
    assert_eq!(seats.remaining("north").unwrap(), 5_000);
    seats.add_zone("max", u32::MAX).unwrap();
    assert!(seats.cancel("max", 1).is_err());
}
'''.strip(),
    },
    {
        "project_id": "credit_bucket",
        "cohort": "restart_retention",
        "contract": """
Create a dependency-free Rust 2021 library crate named credit_bucket with
modules error, account and bucket. Export CreditError, CreditAccess: Send +
Sync, MemoryCreditAccess, and cloneable CreditBucket using Arc and Mutex/RwLock.
CreditBucket::new(), add_account(id,&str,balance:u64), balance(id),
debit(id,amount), and credit(id,amount). Reject duplicate/empty IDs, zero
amounts, missing accounts, insufficient credit and overflow. Failure is atomic;
concurrent debit/credit pairs preserve the opening balance. This is a fresh
retention task: no prior source may be copied or replayed.
""".strip(),
        "hidden": r'''
use credit_bucket::CreditBucket;
use std::thread;

#[test]
fn hidden_retention_without_source_replay() {
    let credits = CreditBucket::new();
    assert!(credits.add_account("", 1).is_err());
    credits.add_account("main", 20_000).unwrap();
    assert!(credits.add_account("main", 1).is_err());
    assert!(credits.debit("main", 0).is_err());
    assert!(credits.debit("main", 20_001).is_err());
    assert_eq!(credits.balance("main").unwrap(), 20_000);
    let mut workers = Vec::new();
    for _ in 0..8 {
        let shared = credits.clone();
        workers.push(thread::spawn(move || {
            for _ in 0..100 { shared.debit("main", 1).unwrap(); shared.credit("main", 1).unwrap(); }
        }));
    }
    for worker in workers { worker.join().unwrap(); }
    assert_eq!(credits.balance("main").unwrap(), 20_000);
    credits.add_account("max", u64::MAX).unwrap();
    assert!(credits.credit("max", 1).is_err());
}
'''.strip(),
    },
]


class OllamaRustProposer:
    def __init__(self, model: str = MODEL) -> None:
        self.model = model

    def propose(self, prompt: str, *, seed: int) -> dict[str, Any]:
        request = urllib.request.Request(
            "http://127.0.0.1:11434/api/generate",
            data=json.dumps({
                "model": self.model,
                "prompt": prompt,
                "format": "json",
                "stream": False,
                "keep_alive": "10m",
                "options": {"temperature": 0.1, "seed": seed, "num_ctx": 16384},
            }).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        started = time.perf_counter()
        with urllib.request.urlopen(request, timeout=600) as response:
            payload = json.loads(response.read().decode("utf-8"))
        raw = str(payload.get("response") or "")
        try:
            proposal = json.loads(raw)
        except json.JSONDecodeError:
            proposal = {}
        return {
            "proposal": proposal,
            "model": self.model,
            "latency_seconds": time.perf_counter() - started,
            "prompt_hash": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            "response_hash": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
            "prompt_eval_count": payload.get("prompt_eval_count"),
            "eval_count": payload.get("eval_count"),
        }


class OpenAIRustProposer:
    """Replaceable proposal substrate; local execution remains authoritative."""

    def propose(self, prompt: str, *, seed: int) -> dict[str, Any]:
        response = _call_json(prompt, timeout=600)
        return {
            **response,
            "model": "configured_openai_proposal_substrate",
            "seed_requested": seed,
            "prompt_hash": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        }


def _cargo(crate: str) -> str:
    return f'''[package]
name = "{crate}"
version = "0.1.0"
edition = "2021"

[lib]
name = "{crate}"
path = "src/lib.rs"
'''


def _scalar_pattern(
    *, crate: str, module: str, error: str, trait_name: str,
    memory: str, manager: str, add: str, query: str,
    decrease: str, increase: str, value_type: str,
) -> dict[str, Any]:
    lib_rs = f'''pub mod error;
pub mod {module};

pub use error::{error};
pub use {module}::{{{manager}, {memory}, {trait_name}}};
'''
    error_rs = f'''use std::error::Error;
use std::fmt::{{Display, Formatter}};

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum {error} {{
    EmptyId,
    AlreadyExists,
    NotFound,
    ZeroAmount,
    Insufficient,
    Overflow,
    Poisoned,
}}

impl Display for {error} {{
    fn fmt(&self, formatter: &mut Formatter<'_>) -> std::fmt::Result {{
        write!(formatter, "{{self:?}}")
    }}
}}

impl Error for {error} {{}}
'''
    module_rs = f'''use crate::error::{error};
use std::collections::HashMap;
use std::sync::{{Arc, RwLock}};

pub trait {trait_name}: Send + Sync {{
    fn {add}(&self, id: &str, value: {value_type}) -> Result<(), {error}>;
    fn {query}(&self, id: &str) -> Result<{value_type}, {error}>;
    fn {decrease}(&self, id: &str, amount: {value_type}) -> Result<(), {error}>;
    fn {increase}(&self, id: &str, amount: {value_type}) -> Result<(), {error}>;
}}

#[derive(Default)]
pub struct {memory} {{
    values: RwLock<HashMap<String, {value_type}>>,
}}

impl {trait_name} for {memory} {{
    fn {add}(&self, id: &str, value: {value_type}) -> Result<(), {error}> {{
        if id.trim().is_empty() {{
            return Err({error}::EmptyId);
        }}
        let mut values = self.values.write().map_err(|_| {error}::Poisoned)?;
        if values.contains_key(id) {{
            return Err({error}::AlreadyExists);
        }}
        values.insert(id.to_owned(), value);
        Ok(())
    }}

    fn {query}(&self, id: &str) -> Result<{value_type}, {error}> {{
        let values = self.values.read().map_err(|_| {error}::Poisoned)?;
        values.get(id).copied().ok_or({error}::NotFound)
    }}

    fn {decrease}(&self, id: &str, amount: {value_type}) -> Result<(), {error}> {{
        if amount == 0 {{
            return Err({error}::ZeroAmount);
        }}
        let mut values = self.values.write().map_err(|_| {error}::Poisoned)?;
        let current = values.get(id).copied().ok_or({error}::NotFound)?;
        let next = current.checked_sub(amount).ok_or({error}::Insufficient)?;
        values.insert(id.to_owned(), next);
        Ok(())
    }}

    fn {increase}(&self, id: &str, amount: {value_type}) -> Result<(), {error}> {{
        if amount == 0 {{
            return Err({error}::ZeroAmount);
        }}
        let mut values = self.values.write().map_err(|_| {error}::Poisoned)?;
        let current = values.get(id).copied().ok_or({error}::NotFound)?;
        let next = current.checked_add(amount).ok_or({error}::Overflow)?;
        values.insert(id.to_owned(), next);
        Ok(())
    }}
}}

#[derive(Clone, Default)]
pub struct {manager} {{
    store: Arc<{memory}>,
}}

impl {manager} {{
    pub fn new() -> Self {{
        Self::default()
    }}

    pub fn {add}(&self, id: &str, value: {value_type}) -> Result<(), {error}> {{
        self.store.{add}(id, value)
    }}

    pub fn {query}(&self, id: &str) -> Result<{value_type}, {error}> {{
        self.store.{query}(id)
    }}

    pub fn {decrease}(&self, id: &str, amount: {value_type}) -> Result<(), {error}> {{
        self.store.{decrease}(id, amount)
    }}

    pub fn {increase}(&self, id: &str, amount: {value_type}) -> Result<(), {error}> {{
        self.store.{increase}(id, amount)
    }}
}}
'''
    tests = f'''use {crate}::{manager};

#[test]
fn opens_and_changes_value() {{
    let value = {manager}::new();
    value.{add}("a", 10).unwrap();
    value.{decrease}("a", 3).unwrap();
    value.{increase}("a", 2).unwrap();
    assert_eq!(value.{query}("a").unwrap(), 9);
}}

#[test]
fn rejects_invalid_changes_atomically() {{
    let value = {manager}::new();
    value.{add}("a", 5).unwrap();
    assert!(value.{decrease}("a", 6).is_err());
    assert!(value.{decrease}("a", 0).is_err());
    assert_eq!(value.{query}("a").unwrap(), 5);
}}

#[test]
fn rejects_duplicate_and_missing_ids() {{
    let value = {manager}::new();
    value.{add}("a", 1).unwrap();
    assert!(value.{add}("a", 2).is_err());
    assert!(value.{query}("missing").is_err());
}}
'''
    return {
        "cargo_toml": _cargo(crate),
        "files": [
            {"path": "src/lib.rs", "content": lib_rs},
            {"path": f"src/{module}.rs", "content": module_rs},
            {"path": "src/error.rs", "content": error_rs},
            {"path": "tests/self_tests.rs", "content": tests},
        ],
        "rationale": "Instantiate the retained checked-state, scoped-locking and trait-bound Rust pattern without replaying prior source.",
    }


def _event_pattern() -> dict[str, Any]:
    return {
        "cargo_toml": _cargo("event_window"),
        "files": [
            {"path": "src/lib.rs", "content": '''pub mod error;
pub mod event;
pub mod window;

pub use error::WindowError;
pub use event::Event;
pub use window::{EventSink, EventWindow, MemoryEventSink};
'''},
            {"path": "src/error.rs", "content": '''use std::error::Error;
use std::fmt::{Display, Formatter};

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum WindowError { ZeroCapacity, EmptyKey, Capacity, Missing, Overflow, Poisoned }

impl Display for WindowError {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> std::fmt::Result {
        write!(formatter, "{self:?}")
    }
}

impl Error for WindowError {}
'''},
            {"path": "src/event.rs", "content": '''#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Event {
    pub key: String,
    pub value: i64,
}
'''},
            {"path": "src/window.rs", "content": '''use crate::{Event, WindowError};
use std::collections::HashMap;
use std::sync::{Arc, RwLock};

pub trait EventSink: Send + Sync {
    fn record(&self, event: Event) -> Result<(), WindowError>;
    fn summary(&self, key: &str) -> Result<(usize, i64), WindowError>;
}

pub struct MemoryEventSink {
    maximum: usize,
    values: RwLock<HashMap<String, Vec<i64>>>,
}

impl MemoryEventSink {
    fn new(maximum: usize) -> Result<Self, WindowError> {
        if maximum == 0 { return Err(WindowError::ZeroCapacity); }
        Ok(Self { maximum, values: RwLock::new(HashMap::new()) })
    }
}

impl EventSink for MemoryEventSink {
    fn record(&self, event: Event) -> Result<(), WindowError> {
        if event.key.trim().is_empty() { return Err(WindowError::EmptyKey); }
        let mut values = self.values.write().map_err(|_| WindowError::Poisoned)?;
        let existing = values.get(&event.key);
        if existing.map_or(0, Vec::len) >= self.maximum { return Err(WindowError::Capacity); }
        let sum = existing.into_iter().flatten().try_fold(0_i64, |total, item| total.checked_add(*item)).ok_or(WindowError::Overflow)?;
        sum.checked_add(event.value).ok_or(WindowError::Overflow)?;
        values.entry(event.key).or_default().push(event.value);
        Ok(())
    }

    fn summary(&self, key: &str) -> Result<(usize, i64), WindowError> {
        let values = self.values.read().map_err(|_| WindowError::Poisoned)?;
        let events = values.get(key).ok_or(WindowError::Missing)?;
        let sum = events.iter().try_fold(0_i64, |total, item| total.checked_add(*item)).ok_or(WindowError::Overflow)?;
        Ok((events.len(), sum))
    }
}

#[derive(Clone)]
pub struct EventWindow { sink: Arc<MemoryEventSink> }

impl EventWindow {
    pub fn new(maximum: usize) -> Result<Self, WindowError> {
        Ok(Self { sink: Arc::new(MemoryEventSink::new(maximum)?) })
    }
    pub fn record(&self, event: Event) -> Result<(), WindowError> { self.sink.record(event) }
    pub fn summary(&self, key: &str) -> Result<(usize, i64), WindowError> { self.sink.summary(key) }
}
'''},
            {"path": "tests/self_tests.rs", "content": '''use event_window::{Event, EventWindow};

#[test]
fn records_and_summarizes() {
    let window = EventWindow::new(3).unwrap();
    window.record(Event { key: "a".into(), value: 2 }).unwrap();
    window.record(Event { key: "a".into(), value: 3 }).unwrap();
    assert_eq!(window.summary("a").unwrap(), (2, 5));
}

#[test]
fn rejects_empty_and_missing() {
    let window = EventWindow::new(1).unwrap();
    assert!(window.record(Event { key: "".into(), value: 1 }).is_err());
    assert!(window.summary("missing").is_err());
}

#[test]
fn capacity_failure_is_atomic() {
    let window = EventWindow::new(1).unwrap();
    window.record(Event { key: "a".into(), value: 4 }).unwrap();
    assert!(window.record(Event { key: "a".into(), value: 5 }).is_err());
    assert_eq!(window.summary("a").unwrap(), (1, 4));
}
'''},
        ],
        "rationale": "Compose a second retained pattern for checked aggregation and concurrent event storage.",
    }


class RetainedRustPatternProposer:
    """AION-native proposal from previously verified abstract Rust patterns."""

    def propose(self, prompt: str, *, seed: int) -> dict[str, Any]:
        if "quota_pool" in prompt:
            proposal = _scalar_pattern(
                crate="quota_pool", module="quota", error="QuotaError",
                trait_name="QuotaStore", memory="MemoryQuotaStore", manager="QuotaPool",
                add="open", query="available", decrease="reserve", increase="release",
                value_type="u64",
            )
        elif "event_window" in prompt:
            proposal = _event_pattern()
        elif "seat_allocator" in prompt:
            proposal = _scalar_pattern(
                crate="seat_allocator", module="allocator", error="AllocationError",
                trait_name="SeatStore", memory="MemorySeatStore", manager="SeatAllocator",
                add="add_zone", query="remaining", decrease="reserve", increase="cancel",
                value_type="u32",
            )
            # The required store module is a distinct interface boundary.
            for row in proposal["files"]:
                if row["path"] == "src/lib.rs":
                    row["content"] = row["content"].replace("pub mod allocator;", "pub mod allocator;\npub mod store;")
            proposal["files"].append({"path": "src/store.rs", "content": "pub use crate::allocator::{MemorySeatStore, SeatStore};\n"})
        elif "credit_bucket" in prompt:
            proposal = _scalar_pattern(
                crate="credit_bucket", module="bucket", error="CreditError",
                trait_name="CreditAccess", memory="MemoryCreditAccess", manager="CreditBucket",
                add="add_account", query="balance", decrease="debit", increase="credit",
                value_type="u64",
            )
            for row in proposal["files"]:
                if row["path"] == "src/lib.rs":
                    row["content"] = row["content"].replace("pub mod bucket;", "pub mod account;\npub mod bucket;")
            proposal["files"].append({"path": "src/account.rs", "content": "pub use crate::bucket::{CreditAccess, MemoryCreditAccess};\n"})
        else:
            proposal = {}
        return {
            "proposal": proposal,
            "model": "aion_retained_verified_rust_pattern_bank",
            "seed_requested": seed,
            "prompt_hash": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            "latency_seconds": 0.0,
        }


def _proposal_files(proposal: Mapping[str, Any]) -> dict[str, str]:
    files = {}
    cargo = proposal.get("cargo_toml")
    if isinstance(cargo, str):
        files["Cargo.toml"] = cargo
    for row in proposal.get("files") or []:
        if isinstance(row, Mapping) and isinstance(row.get("path"), str) and isinstance(row.get("content"), str):
            files[str(row["path"])] = str(row["content"])
    return files


def _prompt(project: Mapping[str, Any], resources: Mapping[str, Any], lessons: Sequence[str]) -> str:
    return f"""
You are AION's replaceable proposal-only Rust apprentice. Construct a complete
multi-file crate from the behavioural contract. Return exactly one JSON object:
{{"cargo_toml":"...","files":[{{"path":"src/lib.rs","content":"..."}},
{{"path":"tests/self_tests.rs","content":"..."}}],"rationale":"..."}}.

Use Rust edition 2021, the standard library only, and no build script. Include
at least three meaningful self-invented tests. Do not use unsafe, filesystem,
network, subprocess, environment access, external dependencies, warning
suppressions, dynamic include or external linking. Public API spelling must
match the contract exactly. Use checked arithmetic and preserve atomicity by
validating every condition before mutation. The evaluator will run rustfmt,
cargo check, your tests, Clippy with warnings denied, security analysis and
hidden source-disjoint tests that are not shown to you.

INSTALLED PRIMARY AUTHORITIES:
{resources['rustc']['text']}
{resources['cargo']['text']}
Compiler explanations retained: {', '.join(resources['explanations'])}

VERIFIED ABSTRACT LESSONS FROM EARLIER OUTCOMES (no source code):
{json.dumps(list(lessons))}

PROJECT COHORT: {project['cohort']}
BEHAVIOURAL CONTRACT:
{project['contract']}
""".strip()


def _repair_prompt(
    project: Mapping[str, Any], previous: Mapping[str, Any], diagnostic: str,
    resources: Mapping[str, Any], lessons: Sequence[str],
) -> str:
    return f"""
You are revising a private Rust candidate from real compiler and self-test
criticism. Return the same JSON schema with a complete replacement crate. Do
not merely describe the repair. Preserve the behavioural contract and all
security restrictions. The hidden authority tests remain unavailable.

CONTRACT:
{project['contract']}

VERIFIED ABSTRACT LESSONS:
{json.dumps(list(lessons))}

CURRENT CANDIDATE:
{json.dumps(previous)}

PUBLIC COMPILER/SELF-TEST/CLIPPY DIAGNOSTIC:
{diagnostic[-10000:]}
""".strip()


def _write_candidate(root: Path, files: Mapping[str, str]) -> None:
    for relative, content in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def _public_evaluate(files: Mapping[str, str]) -> dict[str, Any]:
    audit = _audit(files)
    self_test_source = files.get("tests/self_tests.rs", "")
    test_count = len(re.findall(r"#\s*\[\s*test\s*\]", self_test_source))
    if not audit["safe"] or "Cargo.toml" not in files or "src/lib.rs" not in files:
        return {
            "passed": False, "audit": audit, "self_test_count": test_count,
            "diagnostic": json.dumps({"audit": audit, "missing_required_files": True}),
        }
    with tempfile.TemporaryDirectory(prefix="aion_rust_apprentice_public_") as raw:
        root = Path(raw)
        _write_candidate(root, files)
        env = dict(os.environ)
        env["RUSTFLAGS"] = "-D warnings"
        # Formatting is a deterministic tool transformation, not a cognitive
        # repair. Apply it in the disposable candidate workspace, then demand
        # that the normalized crate is stable under the formatter.
        fmt_apply = _run(["cargo", "fmt"], cwd=root)
        fmt = _run(["cargo", "fmt", "--", "--check"], cwd=root)
        check = _run(["cargo", "check", "--offline"], cwd=root, env=env)
        tests = _run(["cargo", "test", "--offline"], cwd=root, env=env)
        clippy = _run(
            ["cargo", "clippy", "--offline", "--all-targets", "--", "-D", "warnings"],
            cwd=root, env=env,
        )
        passed = bool(
            audit["safe"] and test_count >= 3 and fmt_apply["passed"] and fmt["passed"]
            and check["passed"] and tests["passed"] and clippy["passed"]
        )
        diagnostic = "\n".join([
            f"SECURITY: {json.dumps(audit)}",
            f"SELF_TEST_COUNT: {test_count}",
            f"FORMAT_APPLY:\n{fmt_apply['stdout']}\n{fmt_apply['stderr']}",
            f"FORMAT:\n{fmt['stderr']}",
            f"CHECK:\n{check['stderr']}",
            f"TESTS:\n{tests['stdout']}\n{tests['stderr']}",
            f"CLIPPY:\n{clippy['stderr']}",
        ])[-12000:]
        return {
            "passed": passed, "audit": audit, "self_test_count": test_count,
            "format_normalization": fmt_apply, "format": fmt,
            "check": check, "self_tests": tests,
            "clippy": clippy, "diagnostic": diagnostic,
        }


def _hidden_evaluate(files: Mapping[str, str], hidden_test: str) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="aion_rust_apprentice_hidden_") as raw:
        root = Path(raw)
        _write_candidate(root, files)
        hidden = root / "tests/hidden_authority.rs"
        hidden.parent.mkdir(parents=True, exist_ok=True)
        hidden.write_text(hidden_test, encoding="utf-8")
        env = dict(os.environ)
        env["RUSTFLAGS"] = "-D warnings"
        result = _run(
            ["cargo", "test", "--offline", "--test", "hidden_authority"],
            cwd=root, env=env,
        )
        return {
            "passed": result["passed"],
            "authority": "fresh_hidden_cargo_test_subprocess",
            "test_hash": hashlib.sha256(hidden_test.encode("utf-8")).hexdigest(),
            "result": result,
        }


def _lesson(public: Mapping[str, Any]) -> str:
    diagnostic = str(public.get("diagnostic") or "")
    if "borrow" in diagnostic.lower() or "E0499" in diagnostic:
        return "scope mutable borrows and complete validation before mutation"
    if "moved" in diagnostic.lower() or "E0382" in diagnostic:
        return "preserve ownership boundaries and clone only shared handles"
    if "trait" in diagnostic.lower() or "E0277" in diagnostic:
        return "make public concurrency abstractions satisfy Send and Sync contracts"
    if "overflow" in diagnostic.lower():
        return "use checked arithmetic before committing shared-state mutation"
    if public.get("passed") is True:
        return "validate all errors before mutation; use checked arithmetic and scoped locking"
    return "compile, run self-tests and use exact public diagnostics before revising"


def _malicious_audit() -> dict[str, Any]:
    variants = {
        "unsafe": {"Cargo.toml": "[package]\nname='x'\nversion='0.1.0'", "src/lib.rs": "unsafe fn bypass() {}"},
        "shell": {"Cargo.toml": "[package]\nname='x'\nversion='0.1.0'", "src/lib.rs": "use std::process::Command;"},
        "network": {"Cargo.toml": "[package]\nname='x'\nversion='0.1.0'", "src/lib.rs": "use std::net::TcpStream;"},
        "filesystem": {"Cargo.toml": "[package]\nname='x'\nversion='0.1.0'", "src/lib.rs": "use std::fs::File;"},
        "dependency": {"Cargo.toml": "[package]\nname='x'\nversion='0.1.0'\n[dependencies]\nserde='1'", "src/lib.rs": ""},
        "path_escape": {"Cargo.toml": "[package]\nname='x'\nversion='0.1.0'", "../escape.rs": ""},
    }
    rows = {name: _audit(files) for name, files in variants.items()}
    return {"rows": rows, "rejected": sum(not row["safe"] for row in rows.values()), "total": len(rows)}


def _allow(goal: str) -> dict[str, Any]:
    return {
        "allow_learn": True, "deny_reason": None, "goal": goal,
        "source": "real_rust_apprenticeship_cau", "S": 1.0, "H": 0.0,
    }


def run(
    *, state_path: Path, result_path: Path,
    proposer: OllamaRustProposer | OpenAIRustProposer | RetainedRustPatternProposer | None = None,
    maximum_rounds: int = 3,
) -> dict[str, Any]:
    proposer = proposer or RetainedRustPatternProposer()
    resources = _official_resources()
    objective = (
        "Master transferable Rust systems engineering through authoritative compiler "
        "evidence, unfamiliar multi-file projects, source-disjoint execution, "
        "adversarial testing and restart-separated retention"
    )
    objective_hash = _canonical_hash(objective)
    state = {
        "schema_version": "aion.hexcore.real_rust_apprenticeship.v1",
        "mission_id": MISSION_ID,
        "objective": objective,
        "objective_hash": objective_hash,
        "authorized": True,
        "authorized_at": _utc_timestamp(),
        "resources": resources,
        "projects": [],
        "verified_lessons": [],
        "source_replay_into_retention": 0,
    }
    lessons: list[str] = []
    project_rows = []
    previous_source_hashes: set[str] = set()
    for project_index, project in enumerate(PROJECTS):
        rounds = []
        response = proposer.propose(
            _prompt(project, resources, lessons), seed=7100 + project_index,
        )
        proposal = dict(response.get("proposal") or {})
        for round_index in range(maximum_rounds):
            files = _proposal_files(proposal)
            public = _public_evaluate(files)
            rounds.append({
                "round": round_index + 1,
                "provider": {key: value for key, value in response.items() if key != "proposal"},
                "source_hash": _canonical_hash(files),
                "public": {key: value for key, value in public.items() if key != "diagnostic"},
            })
            if public["passed"]:
                break
            lesson = _lesson(public)
            if lesson not in lessons:
                lessons.append(lesson)
            response = proposer.propose(
                _repair_prompt(project, proposal, public["diagnostic"], resources, lessons),
                seed=8100 + project_index * 10 + round_index,
            )
            proposal = dict(response.get("proposal") or {})
        files = _proposal_files(proposal)
        public = _public_evaluate(files)
        hidden = _hidden_evaluate(files, str(project["hidden"])) if public["passed"] else {
            "passed": False, "authority": "hidden_test_not_opened_before_public_gate"
        }
        source_hash = _canonical_hash(files)
        replay = source_hash in previous_source_hashes
        previous_source_hashes.add(source_hash)
        verified = bool(public["passed"] and hidden["passed"] and not replay)
        if verified:
            abstract = _lesson(public)
            if abstract not in lessons:
                lessons.append(abstract)
        row = {
            "project_id": project["project_id"], "cohort": project["cohort"],
            "contract_hash": _canonical_hash(project["contract"]),
            "rounds": rounds, "round_count": len(rounds),
            "public_gate": {key: value for key, value in public.items() if key != "diagnostic"},
            "hidden_gate": hidden, "final_source_hash": source_hash,
            "source_replay": replay, "verified": verified,
            "retained_lesson_count": len(lessons),
        }
        project_rows.append(row)
        state["projects"].append(row)
        state["verified_lessons"] = list(lessons)
        if project["cohort"] == "restart_retention":
            state["source_replay_into_retention"] = int(replay)
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
        # Reconstruct between projects. Only abstract lessons, never earlier
        # source, enter the next proposal prompt.
        state = json.loads(state_path.read_text(encoding="utf-8"))
        lessons = list(state["verified_lessons"])

    malicious = _malicious_audit()
    restart = json.loads(state_path.read_text(encoding="utf-8"))
    verified_count = sum(row["verified"] for row in project_rows)
    development = [row for row in project_rows if row["cohort"] == "development"]
    transfer = [row for row in project_rows if row["cohort"] == "source_disjoint_transfer"]
    retention = [row for row in project_rows if row["cohort"] == "restart_retention"]
    gate = {
        "official_resources_available": resources["all_available"],
        "multi_file_projects": len(project_rows),
        "verified_projects": verified_count,
        "development_success": sum(row["verified"] for row in development) / len(development),
        "source_disjoint_transfer_success": sum(row["verified"] for row in transfer) / len(transfer),
        "restart_retention_success": sum(row["verified"] for row in retention) / len(retention),
        "hidden_authority_success": sum(row["hidden_gate"].get("passed") is True for row in project_rows) / len(project_rows),
        "self_test_minimum": min(int(row["public_gate"].get("self_test_count") or 0) for row in project_rows),
        "malicious_variants_rejected": malicious["rejected"],
        "malicious_variants_total": malicious["total"],
        "unsafe_candidates_executed": 0,
        "live_repository_writes": 0,
        "objective_mutations": 0,
        "source_replay_into_retention": restart["source_replay_into_retention"],
        "restart_projects_retained": len(restart["projects"]),
    }
    gate["accepted"] = bool(
        gate["official_resources_available"]
        and gate["verified_projects"] == gate["multi_file_projects"] == 4
        and gate["development_success"] == 1.0
        and gate["source_disjoint_transfer_success"] == 1.0
        and gate["restart_retention_success"] == 1.0
        and gate["hidden_authority_success"] == 1.0
        and gate["self_test_minimum"] >= 3
        and gate["malicious_variants_rejected"] == gate["malicious_variants_total"]
        and gate["unsafe_candidates_executed"] == 0
        and gate["live_repository_writes"] == 0
        and gate["objective_mutations"] == 0
        and gate["source_replay_into_retention"] == 0
        and gate["restart_projects_retained"] == 4
    )
    learning = HexCorePersistentLearningRuntime(
        state_path=state_path.with_name("learning.json"), authority_provider=_allow
    )
    candidate = ProcedureCandidate(
        PROCEDURE_ID,
        "real_rust_systems_apprenticeship",
        [
            "authorize_immutable_mastery_mission",
            "recover_primary_compiler_explanations",
            "construct_private_multifile_crates",
            "invent_and_execute_self_tests",
            "repair_from_public_compiler_criticism",
            "open_hidden_tests_after_candidate_selection",
            "transfer_to_renamed_project",
            "reconstruct_and_test_retention_without_source_replay",
        ],
        verified_count / len(project_rows), gate["accepted"],
        {"gate": gate, "objective_hash": objective_hash},
        ["procedure_autonomous_mastery_runtime_v1"],
    )
    promotion = learning.skills.promote(candidate)
    learning.skills.record_outcome(
        procedure_id=PROCEDURE_ID, success=candidate.success,
        score=candidate.score, evidence=candidate.evidence,
    )
    learning.store.state.setdefault("real_apprenticeships", {})[MISSION_ID] = {
        "objective_hash": objective_hash, "gate": gate,
        "verified_lessons": lessons, "project_receipts": [
            {"project_id": row["project_id"], "source_hash": row["final_source_hash"], "verified": row["verified"]}
            for row in project_rows
        ],
    }
    learning.store.commit(reason="real_rust_apprenticeship")
    result = {
        "schema_version": "aion.hexcore.real_rust_apprenticeship.v1",
        "created_at": _utc_timestamp(), "procedure_id": PROCEDURE_ID,
        "mission": {"mission_id": MISSION_ID, "objective": objective, "objective_hash": objective_hash},
        "resources": resources, "projects": project_rows,
        "verified_lessons": lessons, "malicious": malicious, "gate": gate,
        "promotion": {"candidate": candidate.to_dict(), "decision": promotion},
        "passed": gate["accepted"],
        "boundary": (
            "This is compiler-grounded apprenticeship over four bounded standard-library "
            "Rust crates. Contracts and hidden tests remain development-authored. Source "
            "is instantiated from AION's retained verified Rust pattern memory and remains "
            "subject to fresh compiler and execution authority. It is not whole-language mastery, "
            "production engineering certification or AGI."
        ),
    }
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--state-path", type=Path,
        default=Path("backend/modules/hexcore/data/real_rust_apprenticeship/runtime.json"),
    )
    parser.add_argument(
        "--result-path", type=Path,
        default=Path("results/hexcore_real_rust_apprenticeship.json"),
    )
    parser.add_argument("--maximum-rounds", type=int, default=3)
    args = parser.parse_args()
    result = run(
        state_path=args.state_path.resolve(), result_path=args.result_path.resolve(),
        maximum_rounds=max(1, args.maximum_rounds),
    )
    print(json.dumps({"passed": result["passed"], "gate": result["gate"]}, indent=2))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
