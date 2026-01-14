// src/utils/webrtc_e2ee.ts
export async function importAesKey(raw: ArrayBuffer): Promise<CryptoKey> {
  return crypto.subtle.importKey("raw", raw, { name: "AES-GCM" }, false, ["encrypt", "decrypt"]);
}

// Minimal insertable-streams attachment (placeholder transform: wire-up only)
// You can replace the pass-through with real AES-GCM per-frame later.
export function attachSenderE2EE(sender: RTCRtpSender, key: CryptoKey) {
  // @ts-expect-error: createEncodedStreams not yet in TS lib
  const streams = sender.createEncodedStreams?.();
  if (!streams) return;
  const { readable, writable } = streams;
  const transformer = new TransformStream({
    transform: async (chunk: any, controller: any) => {
      // TODO: encrypt chunk.data using AES-GCM with a per-frame IV
      controller.enqueue(chunk); // pass-through for now
    },
  });
  readable.pipeThrough(transformer).pipeTo(writable);
}

export function attachReceiverE2EE(receiver: RTCRtpReceiver, key: CryptoKey) {
  // @ts-expect-error: createEncodedStreams not yet in TS lib
  const streams = receiver.createEncodedStreams?.();
  if (!streams) return;
  const { readable, writable } = streams;
  const transformer = new TransformStream({
    transform: async (chunk: any, controller: any) => {
      // TODO: decrypt chunk.data using AES-GCM with the matching IV
      controller.enqueue(chunk); // pass-through for now
    },
  });
  readable.pipeThrough(transformer).pipeTo(writable);
}