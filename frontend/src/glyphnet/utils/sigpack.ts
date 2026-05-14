// src/utils/sigpack.ts
export const SIG_TAG = "~SIG-";

export function packSig(obj: object): string {
  const b64url = btoa(JSON.stringify(obj))
    .replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  return SIG_TAG + b64url;
}

export function unpackSig(glyph: string): any | null {
  if (typeof glyph !== "string") return null;
  const pos = glyph.indexOf(SIG_TAG);
  if (pos === -1) return null;
  let url = glyph.slice(pos + SIG_TAG.length).trim().replace(/[^A-Za-z0-9\-_]/g, "");
  let b64 = url.replace(/-/g, "+").replace(/_/g, "/");
  while (b64.length % 4) b64 += "=";
  try { return JSON.parse(atob(b64)); } catch { return null; }
}