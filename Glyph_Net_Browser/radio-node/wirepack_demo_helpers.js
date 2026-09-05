import crypto from "crypto";
export function sha256Hex(buf) {
    return crypto.createHash("sha256").update(buf).digest("hex");
}
export function stableStringify(x) {
    const seen = new WeakSet();
    const walk = (v) => {
        if (v === null || typeof v !== "object")
            return v;
        if (seen.has(v))
            throw new Error("cyclic json");
        seen.add(v);
        if (Array.isArray(v))
            return v.map(walk);
        const out = {};
        for (const k of Object.keys(v).sort())
            out[k] = walk(v[k]);
        return out;
    };
    return JSON.stringify(walk(x));
}
export function xorshift32(seed) {
    let x = (seed >>> 0) || 1;
    return () => {
        x ^= (x << 13) >>> 0;
        x ^= (x >>> 17) >>> 0;
        x ^= (x << 5) >>> 0;
        return x >>> 0;
    };
}
export function varintLen(u) {
    let n = u >>> 0;
    let len = 1;
    while (n >= 0x80) {
        n >>>= 7;
        len++;
    }
    return len;
}
export function u32leBytes(arr) {
    const out = Buffer.allocUnsafe(arr.length * 4);
    for (let i = 0; i < arr.length; i++)
        out.writeUInt32LE(arr[i] >>> 0, i * 4);
    return out;
}
export function pickDistinctIndices(R, n, q) {
    const want = Math.max(1, Math.min(q, n));
    const seen = new Set();
    const out = [];
    while (out.length < want) {
        const idx = (R() % n) >>> 0;
        if (!seen.has(idx)) {
            seen.add(idx);
            out.push(idx);
        }
    }
    out.sort((a, b) => a - b);
    return out;
}
// --- v30 helpers ---
export function u64Add(a, b) {
    return (a + b);
}
/** Sum of u32 values addressed by Q over a full n-wide vector. */
export function sumOverQ_full(full, Q) {
    let s = 0n;
    for (let i = 0; i < Q.length; i++)
        s += BigInt(full[Q[i]] >>> 0);
    return s;
}
/** Sum of the tracked projection vector (already aligned with sorted Q). */
export function sumOverQ_tracked(tracked) {
    let s = 0n;
    for (let i = 0; i < tracked.length; i++)
        s += BigInt(tracked[i] >>> 0);
    return s;
}
