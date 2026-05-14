// apps/web/src/lib/qkd.ts

export type LeaseReq = {
  localWA: string;
  remoteWA: string;
  kg: string;
  purpose: string;
};

export type Lease = {
  ok: true;
  kid: string;
  collapse_hash: string;
  salt_b64: string;
  ttl_ms: number;
  fingerprint?: string;
};

export type EncMeta = {
  scheme: "aes-gcm-256/pbkdf2";
  kid: string;
  iv_b64: string;
  aad?: string;
  seq?: number;
  ts?: number;
};

const te = new TextEncoder();
const webCrypto = globalThis.crypto as Crypto;

/* base64 helpers (no spread for big arrays) */
const toB64 = (u8: Uint8Array) => {
  let s = "";
  for (let i = 0; i < u8.length; i++) s += String.fromCharCode(u8[i]);
  return btoa(s);
};
const fromB64 = (s: string) => {
  const bin = atob(s);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
};

/* 12-byte IV for AES-GCM */
const randIV12 = () => {
  const iv = new Uint8Array(12);
  webCrypto.getRandomValues(iv);
  return iv;
};

export async function qkdLease(req: LeaseReq): Promise<Lease> {
  const r = await fetch("/qkd/lease", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  const j = await r.json();
  if (!j?.ok) throw new Error(j?.error || "QKD lease failed");
  return j as Lease;
}

/* PBKDF2(SHA-256) -> AES-GCM key */
async function deriveAESGCMKey(collapseHash: string, saltB64: string): Promise<CryptoKey> {
  const raw = te.encode(collapseHash); // Uint8Array
  const baseKey = await webCrypto.subtle.importKey("raw", raw, "PBKDF2", false, ["deriveKey"]);
  return webCrypto.subtle.deriveKey(
    {
      name: "PBKDF2",
      // IMPORTANT: older DOM lib wants ArrayBuffer, not ArrayBufferLike
      salt: fromB64(saltB64).buffer as ArrayBuffer,
      iterations: 100_000,
      hash: "SHA-256",
    },
    baseKey,
    { name: "AES-GCM", length: 256 },
    false,
    ["encrypt", "decrypt"]
  );
}

export async function qkdEncrypt(
  lease: Lease,
  plaintext: Uint8Array,
  aad = "",
  seq?: number
) {
  const key = await deriveAESGCMKey(lease.collapse_hash, lease.salt_b64);
  const iv = randIV12();

  const params: AesGcmParams = {
    name: "AES-GCM",
    iv, // Uint8Array is fine
    // Pass ArrayBuffer explicitly to satisfy strict DOM typings
    additionalData: aad ? (te.encode(aad).buffer as ArrayBuffer) : undefined,
  };

  // Ensure we pass exactly the view range as ArrayBuffer
  const msgAb = plaintext.buffer.slice(
    plaintext.byteOffset,
    plaintext.byteOffset + plaintext.byteLength
  ) as ArrayBuffer;

  const ab = await webCrypto.subtle.encrypt(params, key, msgAb);

  const data_b64 = toB64(new Uint8Array(ab));
  const enc: EncMeta = {
    scheme: "aes-gcm-256/pbkdf2",
    kid: lease.kid,
    iv_b64: toB64(iv),
    aad,
    seq,
    ts: Date.now(),
  };
  return { data_b64, enc };
}

export async function qkdDecrypt(
  lease: Lease,
  encMeta: EncMeta,
  data_b64: string,
  aad = ""
): Promise<Uint8Array> {
  const key = await deriveAESGCMKey(lease.collapse_hash, lease.salt_b64);
  const iv = fromB64(encMeta.iv_b64);

  const params: AesGcmParams = {
    name: "AES-GCM",
    iv,
    additionalData: aad ? (te.encode(aad).buffer as ArrayBuffer) : undefined,
  };

  // Ciphertext as ArrayBuffer to appease older DOM lib
  const ctAb = (fromB64(data_b64).buffer as ArrayBuffer);

  const ab = await webCrypto.subtle.decrypt(params, key, ctAb);
  return new Uint8Array(ab);
}