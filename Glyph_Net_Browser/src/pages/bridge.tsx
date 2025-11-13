// src/pages/bridge.tsx
import { useEffect, useRef, useState } from "react";

export default function BridgePage() {
  const [status, setStatus] = useState("idle");
  const wsRef = useRef<WebSocket | null>(null);
  const writerRef = useRef<WritableStreamDefaultWriter<Uint8Array> | null>(null);

  const token = (import.meta as any)?.env?.VITE_BRIDGE_TOKEN || "dev-bridge";
  const wsUrl = (() => {
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    return `${proto}//${location.host}/ws/rflink?token=${encodeURIComponent(token)}`;
  })();

  async function connectSerial() {
    if (!("serial" in navigator)) {
      alert("WebSerial not available in this browser.");
      return;
    }
    setStatus("requesting-port");
    // Ask user to pick the RF dongle
    const port = await (navigator as any).serial.requestPort();
    await port.open({ baudRate: 115200 });
    const writer = port.writable.getWriter();
    writerRef.current = writer;

    // Data from device -> send to server as RF RX
    const reader = port.readable.getReader();
    setStatus("serial-open");

    (async () => {
      try {
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          if (value && wsRef.current?.readyState === WebSocket.OPEN) {
            // For now we assume the device sends (topic|bytes) in a raw frame.
            // If your firmware uses a custom protocol, parse it here and set topic/codec.
            const bytes_b64 = btoa(String.fromCharCode(...value));
            wsRef.current.send(
              JSON.stringify({
                type: "rx",
                topic: "personal:ucs://local/voice", // TODO: fill actual topic
                bytes_b64,
              })
            );
          }
        }
      } catch {}
      try { reader.releaseLock(); } catch {}
    })();

    // WS: server -> device (RF TX)
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => setStatus("bridge-connected");
    ws.onmessage = async (e) => {
      try {
        const msg = JSON.parse(e.data);
        if (msg?.type === "tx" && msg?.bytes_b64 && writerRef.current) {
          const bin = Uint8Array.from(atob(msg.bytes_b64), c => c.charCodeAt(0));
          await writerRef.current.write(bin);
        }
      } catch {}
    };
    ws.onclose = () => setStatus("bridge-ws-closed");
    ws.onerror = () => setStatus("bridge-ws-error");
  }

  return (
    <div style={{ padding: 24 }}>
      <h1>Radio Bridge</h1>
      <p>Status: {status}</p>
      <button onClick={connectSerial}>Connect Serial & Bridge</button>
      <p style={{opacity:.7, marginTop:12}}>
        After connecting, frames from the node will be pushed to the device,
        and bytes from the device will be posted back to the node as RF RX.
      </p>
    </div>
  );
}