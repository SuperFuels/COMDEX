#!/usr/bin/env python3
"""
bv46b — Cross-language codec test vectors (Python ↔ Rust)

Claim:
- bit-identical encoding across Python and Rust for GlyphOS WirePack v1.

Policy:
- Uses GlyphOS WirePack codec (encode_template/encode_delta/canonicalize_delta/encode_delta_stream).
- Lean compile check uses:
    backend/modules/lean/workspace/SymaticsBridge/V46_CrossLangWirePackVectors.lean
- If Lean fails, LEAN_OK=(1 if int(__import__("os").environ.get("REQUIRE_LEAN","0")) else 0) and benchmark still succeeds unless REQUIRE_LEAN=1.
- If UPDATE_LOCKS=1:
    - writes backend/tests/locks/v46_crosslang_vectors_out.txt itself (NO tee needed)
    - writes backend/tests/locks/v46_crosslang_vectors_lock.sha256 using sha256(Lean file) and sha256(out file)

Rust:
- Expects Rust binary at:
    tools/glyphos_wirepack_v46_vectors.bin
  The binary MUST read vectors JSON from stdin and print RUST_OK=1 on success.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.modules.glyphos.wirepack_codec import (  # noqa: E402
    canonicalize_delta,
    encode_delta,
    encode_delta_stream,
    encode_template,
)

# -------------------- locked params --------------------

SEED = 46046
N_ITEMS = 4096
K_UPDATES = 1024
M_EDITS = 4
VAL_MIN = -1_000_000
VAL_MAX = 1_000_000

REQUIRE_LEAN = os.environ.get("REQUIRE_LEAN", "1") == "1"
UPDATE_LOCKS = os.environ.get("UPDATE_LOCKS", "0") == "1"

# -------------------- paths --------------------

LEAN_REL = "SymaticsBridge/V46_CrossLangWirePackVectors.lean"
LEAN_WS = ROOT / "backend/modules/lean/workspace"
LEAN_FILE = LEAN_WS / LEAN_REL
THIS_FILE = Path(__file__).resolve()

LOCK_DIR = ROOT / "backend/tests/locks"
OUT_FILE = LOCK_DIR / "v46_crosslang_vectors_out.txt"
LOCK_SHA = LOCK_DIR / "v46_crosslang_vectors_lock.sha256"

RUST_BIN = ROOT / "tools/glyphos_wirepack_v46_vectors.bin"

# -------------------- helpers --------------------

def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def stable_json(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def lean_check() -> int:
    if not LEAN_FILE.exists():
        return 0
    r = subprocess.run(
        ["lake", "env", "lean", LEAN_REL],
        cwd=str(LEAN_WS),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return 1 if r.returncode == 0 else 0

# -------------------- vector generation --------------------

Op = Tuple[int, int]  # (idx, value)

def gen_vectors() -> dict:
    rng = random.Random(SEED)

    base = [0 for _ in range(N_ITEMS)]
    template = encode_template(base)

    deltas_can: List[bytes] = []
    for _ in range(K_UPDATES):
        ops: List[Op] = []
        for _ in range(M_EDITS):
            ops.append((rng.randrange(0, N_ITEMS), rng.randrange(VAL_MIN, VAL_MAX)))
        d = canonicalize_delta(encode_delta(ops))
        deltas_can.append(d)

    delta_stream = encode_delta_stream(deltas_can)

    # publish as hex to keep JSON simple and deterministic
    vectors = {
        "codec": "wirepack_v1",
        "seed": SEED,
        "n_items": N_ITEMS,
        "k_updates": K_UPDATES,
        "m_edits": M_EDITS,
        "template_hex": template.hex(),
        "delta_stream_hex": delta_stream.hex(),
        "template_sha256": sha256_hex(template),
        "delta_stream_sha256": sha256_hex(delta_stream),
    }
    return vectors

def rust_verify(vectors: dict) -> int:
    if not RUST_BIN.exists():
        return 0
    p = subprocess.run(
        [str(RUST_BIN)],
        input=(json.dumps(vectors) + "\n").encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    # Rust tool should print RUST_OK=1 on success
    out = p.stdout.decode("utf-8", errors="replace")
    ok = (p.returncode == 0) and ("RUST_OK=1" in out)
    return 1 if ok else 0

def main() -> None:
    vectors = gen_vectors()
    rust_ok = rust_verify(vectors)

    receipt = {
        "codec": vectors["codec"],
        "seed": vectors["seed"],
        "n_items": vectors["n_items"],
        "k_updates": vectors["k_updates"],
        "m_edits": vectors["m_edits"],
        "template_sha256": vectors["template_sha256"],
        "delta_stream_sha256": vectors["delta_stream_sha256"],
        "rust_ok": bool(rust_ok),
    }
    drift_sha256 = sha256_hex(stable_json(receipt))

    out_lines: List[str] = []
    a = out_lines.append

    a("=== ✅ Bridge Benchmark bv46b: Cross-language WirePack codec vectors (Python ↔ Rust) ===")
    a("v46_crosslang_vectors_wirepack")
    a(f"seed={SEED}")
    a(f"n_items={N_ITEMS} k_updates={K_UPDATES} m_edits={M_EDITS}")
    a(f"template_sha256={vectors['template_sha256']}")
    a(f"delta_stream_sha256={vectors['delta_stream_sha256']}")
    a(f"rust_ok={bool(rust_ok)}")
    a(f"drift_sha256={drift_sha256}")
    a("")
    LEAN_OK = lean_check()
    a(f"LEAN_OK={LEAN_OK}")
    a("")
    a("SHA256 (bv46b)")
    a("")
    if LEAN_FILE.exists():
        a(f"{sha256_file(LEAN_FILE)}  {LEAN_FILE.as_posix()}")
    else:
        a(f"<missing>  {LEAN_FILE.as_posix()}")
    a(f"{sha256_file(THIS_FILE)}  {THIS_FILE.as_posix()}")

    out_text = "\n".join(out_lines) + "\n"

    if UPDATE_LOCKS:
        LOCK_DIR.mkdir(parents=True, exist_ok=True)
        OUT_FILE.write_text(out_text, encoding="utf-8")

    sys.stdout.write(out_text)
    sys.stdout.flush()

    # assertions
    assert rust_ok == 1, "Rust verifier must succeed (RUST_OK=1)"
    if REQUIRE_LEAN:
        assert LEAN_OK == 1, "Lean bridge file must compile (lake env lean ...)"

    if UPDATE_LOCKS:
        lean_sha = sha256_file(LEAN_FILE)
        out_sha = hashlib.sha256(out_text.encode("utf-8")).hexdigest()
        LOCK_SHA.write_text(
            f"{lean_sha}  backend/modules/lean/workspace/{LEAN_REL}\n"
            f"{out_sha}  backend/tests/locks/{OUT_FILE.name}\n",
            encoding="utf-8",
        )
        print(f"wrote {LOCK_SHA.as_posix()}", file=sys.stderr)

if __name__ == "__main__":
    main()
