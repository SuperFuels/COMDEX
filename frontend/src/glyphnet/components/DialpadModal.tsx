import React, { useState } from "react";

export default function DialpadModal({
  base, topic, graph, agentId, onClose,
}: { base: string; topic: string; graph: "personal"|"work"; agentId: string; onClose: () => void; }) {
  const [num, setNum] = useState("");

  const valid = /^\+?[1-9]\d{6,15}$/.test(num.trim());

  async function dial() {
    if (!valid) return;
    const call_id = crypto?.randomUUID?.() || `pstn-${Date.now()}`;
    // For now: emit a stub “outbound PSTN dialing…” message.
    // Later: integrate your TwiML <Dial> bridge or a server-initiated PSTN leg.
    await fetch(`${base}/api/glyphnet/tx`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Agent-Token": "dev-token", "X-Agent-Id": agentId },
      body: JSON.stringify({
        recipient: topic,
        graph,
        capsule: { glyphs: [`☎️ Dialing ${num}…`] },
        meta: { pstn: true, to_e164: num, call_id, trace_id: agentId, t0: Date.now() }
      })
    });
    onClose();
  }

  return (
    <div style={{ padding: 12, border: "1px solid #e5e7eb", borderRadius: 8, background: "#fff" }}>
      <div style={{ fontWeight: 600, marginBottom: 8 }}>Dial a number</div>
      <input
        autoFocus
        placeholder="+15551234567"
        value={num}
        onChange={(e) => setNum(e.target.value)}
        style={{ width: 220, padding: 8, border: "1px solid #ddd", borderRadius: 6, marginRight: 8 }}
      />
      <button disabled={!valid} onClick={dial} style={{ padding: "8px 12px", borderRadius: 6 }}>
        Call
      </button>
      <button onClick={onClose} style={{ marginLeft: 8, padding: "8px 12px", borderRadius: 6 }}>
        Cancel
      </button>
      {!valid && num.length > 0 && (
        <div style={{ fontSize: 12, color: "#b91c1c", marginTop: 6 }}>Enter a valid E.164 number.</div>
      )}
    </div>
  );
}