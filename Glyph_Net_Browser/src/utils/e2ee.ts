// AES-GCM insertable streams (demo only; rotate keys per call in production)
export async function importAesKey(raw: ArrayBuffer) {
  return crypto.subtle.importKey("raw", raw, "AES-GCM", false, ["encrypt", "decrypt"]);
}

export function attachSenderE2EE(sender: RTCRtpSender, key: CryptoKey) {
  // @ts-ignore
  const { readable, writable } = sender.createEncodedStreams();
  const reader = readable.getReader();
  const writer = writable.getWriter();

  (async () => {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      // value: RTCEncodedAudioFrame (with .data: ArrayBuffer)
      const frame: any = value;
      const iv = crypto.getRandomValues(new Uint8Array(12));
      const data = new Uint8Array(frame.data);
      const enc = await crypto.subtle.encrypt({ name: "AES-GCM", iv }, key, data);
      frame.data = new Uint8Array(enc);
      // attach iv to metadata header (abuse "dependencyDescriptor" or insert prefix)
      frame.metadata = frame.metadata || {};
      frame.metadata.iv = Array.from(iv);
      await writer.write(frame);
    }
  })();
}

export function attachReceiverE2EE(receiver: RTCRtpReceiver, key: CryptoKey) {
  // @ts-ignore
  const { readable, writable } = receiver.createEncodedStreams();
  const reader = readable.getReader();
  const writer = writable.getWriter();

  (async () => {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      const frame: any = value;
      const ivArr = (frame.metadata && frame.metadata.iv) || null;
      if (!ivArr) { await writer.write(frame); continue; }
      const iv = new Uint8Array(ivArr);
      const data = new Uint8Array(frame.data);
      try {
        const dec = await crypto.subtle.decrypt({ name: "AES-GCM", iv }, key, data);
        frame.data = new Uint8Array(dec);
      } catch {
        // drop if decrypt fails
      }
      await writer.write(frame);
    }
  })();
}