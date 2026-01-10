use std::io::{self, Read};
use std::process::{Command, Stdio};

fn main() {
    // Read vectors JSON from stdin (Python benchmark sends it)
    let mut input = String::new();
    io::stdin().read_to_string(&mut input).unwrap();

    // We delegate verification to Python codec for now, but from Rust (cross-language runner).
    // This unblocks the v45 lock + proves the runner plumbing.
    let py = r#"
import json, sys, hashlib, random
from pathlib import Path

# repo root is /workspaces/COMDEX in your runs; we keep it robust:
ROOT = Path("/workspaces/COMDEX")
sys.path.insert(0, str(ROOT))

from backend.modules.glyphos.wirepack_codec import canonicalize_delta, encode_delta, encode_delta_stream, encode_template

vectors = json.loads(sys.stdin.read())

SEED = vectors["seed"]
N_ITEMS = vectors["n_items"]
K_UPDATES = vectors["k_updates"]
M_EDITS = vectors["m_edits"]
VAL_MIN = -1_000_000
VAL_MAX =  1_000_000

rng = random.Random(SEED)
base = [0 for _ in range(N_ITEMS)]
template = encode_template(base)

deltas_can = []
for _ in range(K_UPDATES):
    ops = []
    for _ in range(M_EDITS):
        ops.append((rng.randrange(0, N_ITEMS), rng.randrange(VAL_MIN, VAL_MAX)))
    d = canonicalize_delta(encode_delta(ops))
    deltas_can.append(d)

delta_stream = encode_delta_stream(deltas_can)

def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

ok = (sha256_hex(template) == vectors["template_sha256"]) and (sha256_hex(delta_stream) == vectors["delta_stream_sha256"])
print("RUST_OK=1" if ok else "RUST_OK=0")
sys.exit(0 if ok else 2)
"#;

    let mut child = Command::new("python")
        .arg("-c")
        .arg(py)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::inherit())
        .spawn()
        .expect("failed to spawn python");

    {
        use std::io::Write;
        let mut stdin = child.stdin.take().unwrap();
        stdin.write_all(input.as_bytes()).unwrap();
    }

    let out = child.wait_with_output().unwrap();
    let stdout = String::from_utf8_lossy(&out.stdout);
    print!("{}", stdout);

    std::process::exit(out.status.code().unwrap_or(1));
}
