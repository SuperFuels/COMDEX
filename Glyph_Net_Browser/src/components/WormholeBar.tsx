import { useMemo, useState } from "react";

type Mode = "wormhole" | "http";

export default function WormholeBar(props: {
  onNavigate: (t: { mode: Mode; address: string }) => void;
}) {
  const [mode, setMode] = useState<Mode>("wormhole");
  const [value, setValue] = useState("");

  const placeholder = useMemo(
    () =>
      mode === "wormhole"
        ? "nike  •  partner.home  •  kevin.tp"
        : "www.wikipedia.org",
    [mode]
  );

  function normalizeWormhole(input: string): string {
    let v = input.trim();
    v = v.replace(/^🌀/u, "");         // strip emoji if pasted
    if (!/\.tp$/i.test(v)) v = `${v}.tp`; // ensure .tp
    return `🌀${v}`;                   // canonical display
  }

  function toContainerId(input: string): string {
    // produce bare id used by #/container/<id>
    let v = input.trim();
    v = v.replace(/^🌀/u, "");
    v = v.replace(/\.tp$/i, "");
    return v;
  }

  function normalizeHttp(input: string): string {
    const v = input.trim();
    if (/^https?:\/\//i.test(v)) return v;
    if (v.startsWith("www.")) return `https://${v}`;
    if (v.includes(".")) return `https://${v}`;
    return `https://www.google.com/search?q=${encodeURIComponent(v)}`;
  }

  function inferModeFromValue(v: string): Mode {
    const s = v.trim();
    if (/^https?:\/\//i.test(s) || s.startsWith("www.") || s.includes("."))
      return "http";
    return "wormhole";
  }

  function go() {
    if (!value.trim()) return;

    if (mode === "wormhole") {
      const addr = normalizeWormhole(value);   // 🌀name.tp
      const cid = toContainerId(addr);         // name

      // keep original callback contract
      props.onNavigate({ mode, address: addr });

      // 🔗 drive the SPA directly
      window.location.hash = `#/container/${encodeURIComponent(cid)}`;

      // 📣 notify any listeners that rely on the event
      const reply = { to: cid, name: `${cid}.tp` };
      window.dispatchEvent(
        new CustomEvent("wormhole:resolved", { detail: reply })
      );
    } else {
      const url = normalizeHttp(value);
      props.onNavigate({ mode, address: url });
      // You can also navigate immediately if desired:
      // window.location.href = url;
    }
  }

  return (
    <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
      {/* Mode toggle pill */}
      <div
        role="group"
        aria-label="Transport mode"
        style={{
          display: "inline-flex",
          border: "1px solid #cbd5e1",
          borderRadius: 999,
          overflow: "hidden",
        }}
      >
        <button
          onClick={() => setMode("wormhole")}
          title="Wormhole (🌀)"
          style={{
            padding: "6px 10px",
            border: "none",
            cursor: "pointer",
            background: mode === "wormhole" ? "#111827" : "transparent",
            color: mode === "wormhole" ? "#fff" : "#111827",
          }}
        >
          🌀
        </button>
        <button
          onClick={() => setMode("http")}
          title="Legacy Web (www)"
          style={{
            padding: "6px 10px",
            border: "none",
            cursor: "pointer",
            background: mode === "http" ? "#111827" : "transparent",
            color: mode === "http" ? "#fff" : "#111827",
          }}
        >
          www
        </button>
      </div>

      <input
        value={value}
        onChange={(e) => {
          const v = e.target.value;
          setValue(v);
          // QoL: auto-switch to http if user types http/www
          const inferred = inferModeFromValue(v);
          if (inferred !== mode && (v.startsWith("http") || v.startsWith("www."))) {
            setMode(inferred);
          }
        }}
        placeholder={placeholder}
        onKeyDown={(e) => {
          if (e.key === "Enter") go();
        }}
        style={{
          flex: 1,
          padding: "8px 12px",
          borderRadius: 8,
          border: "1px solid #cbd5e1",
          outline: "none",
        }}
      />
      <button
        onClick={go}
        style={{
          padding: "8px 14px",
          borderRadius: 8,
          background: "#111827",
          color: "#fff",
          border: "none",
          cursor: "pointer",
        }}
      >
        Go
      </button>
    </div>
  );
}