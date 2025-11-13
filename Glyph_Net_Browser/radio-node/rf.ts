// radio-node/rf.ts
export type RFFrame = {
  topic: string;
  seq: number;
  ts: number;
  codec?: string;
  bytes: Uint8Array;
};

const seqByTopic = new Map<string, number>();
export function nextSeq(topic: string) {
  const n = (seqByTopic.get(topic) ?? 0) + 1;
  seqByTopic.set(topic, n);
  return n;
}

export function encodeFrame(f: RFFrame): Uint8Array {
  const codecBytes = new TextEncoder().encode(f.codec ?? "");
  const topicBytes = new TextEncoder().encode(f.topic);
  const headerLen = 1 + 4 + 8 + 1 + codecBytes.length + 1 + topicBytes.length;
  const out = new Uint8Array(headerLen + f.bytes.length);
  const dv = new DataView(out.buffer);

  let o = 0;
  out[o++] = 1;
  dv.setUint32(o, f.seq >>> 0, false); o += 4;

  const hi = Math.floor(f.ts / 2 ** 32);
  const lo = f.ts >>> 0;
  dv.setUint32(o, hi >>> 0, false); o += 4;
  dv.setUint32(o, lo >>> 0, false); o += 4;

  out[o++] = codecBytes.length & 0xff;
  out.set(codecBytes, o); o += codecBytes.length;

  out[o++] = topicBytes.length & 0xff;
  out.set(topicBytes, o); o += topicBytes.length;

  out.set(f.bytes, o);
  return out;
}