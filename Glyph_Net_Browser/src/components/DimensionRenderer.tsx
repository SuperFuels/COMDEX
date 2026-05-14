// src/components/DimensionRenderer.tsx
import type { DcContainer } from "@/lib/types/dc";

export default function DimensionRenderer({ dc }: { dc: DcContainer }) {
  const glyphs = dc.glyphs ?? [];

  return (
    <div style={{ padding: 12, border: "1px solid #e5e7eb", borderRadius: 8, background: "#fff" }}>
      <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
        <h3 style={{ margin: 0 }}>{dc.id}</h3>
        <span style={{ fontSize: 12, color: "#64748b" }}>{dc.type}</span>
      </div>

      {dc.meta?.address && (
        <div style={{ marginTop: 6, color: "#334155" }}>
          <code>{dc.meta.address}</code>
        </div>
      )}

      <div style={{ marginTop: 10 }}>
        <strong>Glyphs:</strong> {glyphs.length}
      </div>

      {glyphs.length > 0 && (
        <ul style={{ marginTop: 8 }}>
          {glyphs.slice(0, 20).map((g, i) => (
            <li key={g.id ?? i} style={{ fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace" }}>
              {g.symbol ? `${g.symbol} ` : ""}{g.text ?? ""} {g.id ? `(${g.id})` : ""}
            </li>
          ))}
        </ul>
      )}

      {dc.meta && (
        <details style={{ marginTop: 10 }}>
          <summary style={{ cursor: "pointer" }}>meta</summary>
          <pre style={{ marginTop: 8, background: "#f8fafc", padding: 8, borderRadius: 6, overflow: "auto" }}>
{JSON.stringify(dc.meta, null, 2)}
          </pre>
        </details>
      )}
    </div>
  );
}