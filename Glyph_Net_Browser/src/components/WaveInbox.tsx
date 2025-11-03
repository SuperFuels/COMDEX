// src/components/WaveInbox.tsx
import { useState } from "react";
type Wave = { id: string; from: string; subject: string; ts: string; unread?: boolean };
const MOCK: Wave[] = [
  { id: "w1", from: "kevin.tp", subject: "Welcome to GlyphNet", ts: "now", unread: true },
  { id: "w2", from: "partner.home", subject: "Invite: bond", ts: "2h" },
];
export default function WaveInbox() {
  const [waves, setWaves] = useState(MOCK);
  return (
    <div style={{ padding: 12 }}>
      <h3>Waves</h3>
      <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
        {waves.map(w => (
          <li key={w.id} style={{ padding: "8px 10px", borderBottom: "1px solid #eee" }}>
            <strong>{w.unread ? "• " : ""}{w.subject}</strong>
            <div style={{ opacity: .7 }}>{w.from} · {w.ts}</div>
          </li>
        ))}
      </ul>
    </div>
  );
}