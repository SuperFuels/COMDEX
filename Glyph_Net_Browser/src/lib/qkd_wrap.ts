// apps/web/src/lib/qkd_wrap.ts
import { qkdEncrypt, type EncMeta } from "./qkd";
import { getLease, bumpSeq, currentSeq } from "./qkd_cache";

export type ProtectArgs = {
  capsule: any;
  localWA: string;     // your identity (ucs://…)
  remoteWA: string;    // their identity (ucs://… or recipient field)
  kg: string;          // graph, e.g., "personal"
};

function b64ToU8(s: string) {
  const bin = atob(s);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

export async function protectCapsule({ capsule, localWA, remoteWA, kg }: ProtectArgs) {
  // shallow clone so we don’t mutate caller
  const c = JSON.parse(JSON.stringify(capsule)) as any;

  // decide what we’re encrypting (prefer voice over glyph if mixed)
  let purpose: "glyph" | "voice_note" | "voice_frame" | null = null;
  if (c.voice_frame?.data_b64) purpose = "voice_frame";
  else if (c.voice_note?.data_b64) purpose = "voice_note";
  else if (Array.isArray(c.glyphs) && c.glyphs.length) purpose = "glyph";

  if (!purpose) return { capsule: c, used: null as EncMeta | null };

  const { lease } = await getLease(purpose, kg, localWA, remoteWA);
  const seq = currentSeq(purpose, kg, localWA, remoteWA);

  let encMeta: EncMeta | null = null;

  if (purpose === "glyph") {
    const textBytes = new TextEncoder().encode(JSON.stringify(c.glyphs));
    const { data_b64, enc } = await qkdEncrypt(lease, textBytes, "glyph", seq);
    c.glyphs_enc_b64 = data_b64;
    delete c.glyphs;
    c.enc = enc;
    encMeta = enc;
  } else if (purpose === "voice_note") {
    const { data_b64, enc } = await qkdEncrypt(lease, b64ToU8(c.voice_note.data_b64), "voice_note", seq);
    c.voice_note.data_b64 = data_b64;
    c.enc = enc;
    encMeta = enc;
  } else if (purpose === "voice_frame") {
    const { data_b64, enc } = await qkdEncrypt(lease, b64ToU8(c.voice_frame.data_b64), "voice_frame", seq);
    c.voice_frame.data_b64 = data_b64;
    c.enc = enc;
    encMeta = enc;
  }

  bumpSeq(purpose, kg, localWA, remoteWA);
  return { capsule: c, used: encMeta };
}