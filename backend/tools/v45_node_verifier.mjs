import crypto from "crypto";

function xs32(seed) {
  let x = (seed >>> 0) || 0x6d2b79f5;
  return () => {
    x ^= (x << 13) >>> 0;
    x ^= (x >>> 17) >>> 0;
    x ^= (x << 5) >>> 0;
    return x >>> 0;
  };
}

function u32ToI32(u) {
  u >>>= 0;
  return (u & 0x80000000) ? (u - 0x100000000) : u;
}

function zzEncI32(n) {
  n |= 0;
  return (((n << 1) ^ (n >> 31)) >>> 0);
}
function varintEnc(u) {
  u = Number(u);
  if (u < 0) throw new Error("varint expects non-negative");
  const out = [];
  while (true) {
    const b = u & 0x7f;
    u = Math.floor(u / 128);
    if (u) out.push(b | 0x80);
    else { out.push(b); break; }
  }
  return Buffer.from(out);
}

const MAGIC_T = Buffer.from("WP45T");
const MAGIC_D = Buffer.from("WP45D");

function encTemplate(state0) {
  const chunks = [MAGIC_T, varintEnc(state0.length)];
  for (const v of state0) chunks.push(varintEnc(zzEncI32(v | 0)));
  return Buffer.concat(chunks);
}

function encDeltas(deltas) {
  const chunks = [MAGIC_D, varintEnc(deltas.length)];
  for (const [idx, oldv, newv] of deltas) {
    chunks.push(varintEnc(idx));
    chunks.push(varintEnc(zzEncI32(oldv | 0)));
    chunks.push(varintEnc(zzEncI32(newv | 0)));
  }
  return Buffer.concat(chunks);
}

function sha256Hex(buf) {
  return crypto.createHash("sha256").update(buf).digest("hex");
}

function sha256StateI32(st) {
  const bb = Buffer.alloc(st.length * 4);
  for (let i = 0; i < st.length; i++) {
    const x = (st[i] >>> 0);
    bb.writeUInt32LE(x, i * 4);
  }
  return sha256Hex(bb);
}

function simulate(seed, n, turns, muts) {
  const rng = xs32(seed);
  const ops = turns * muts;

  const state0 = new Array(n);
  const st = new Array(n);
  for (let i = 0; i < n; i++) {
    let v = u32ToI32(rng());
    v = (v % 10000) | 0;
    state0[i] = v;
    st[i] = v;
  }

  const deltas = [];
  for (let k = 0; k < ops; k++) {
    const idx = (rng() % n) | 0;
    const oldv = st[idx] | 0;
    const d = ((rng() % 11) - 5) | 0;
    const newv = (oldv + d) | 0;
    deltas.push([idx, oldv, newv]);
    st[idx] = newv;
  }

  return { state0, deltas, final: st };
}

const [seedS, nS, turnsS, mutsS] = process.argv.slice(2);
const seed = Number(seedS || 0);
const n = Number(nS || 0);
const turns = Number(turnsS || 0);
const muts = Number(mutsS || 0);

const { state0, deltas, final } = simulate(seed, n, turns, muts);

const template = encTemplate(state0);
const delta = encDeltas(deltas);

const out = {
  template_b64: template.toString("base64"),
  delta_b64: delta.toString("base64"),
  template_sha256: sha256Hex(template),
  delta_stream_sha256: sha256Hex(delta),
  final_state_sha256: sha256StateI32(final),
};

process.stdout.write(JSON.stringify(out));