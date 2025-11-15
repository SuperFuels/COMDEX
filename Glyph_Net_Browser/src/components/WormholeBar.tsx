import React, { useMemo, useRef, useState } from "react";
import { classifyAddress } from "@/lib/nav/parse";

type Mode = "wormhole" | "http";
type NavArg = string | { mode: Mode; address: string };

export default function WormholeBar({ onNavigate }: { onNavigate: (arg: NavArg) => void }) {
  const [mode, setMode] = useState<Mode>("wormhole");
  const ref = useRef<HTMLInputElement>(null);

  const placeholder = useMemo(
    () => (mode === "wormhole" ? "nike • partner.home • kevin.tp" : "www.wikipedia.org"),
    [mode]
  );

  const ensureHttp = (v: string) => {
    if (/^https?:\/\//i.test(v)) return v;
    if (v.startsWith("www.")) return `https://${v}`;
    return `https://${v}`;
  };

  const normWormhole = (v: string) => {
    let name = v.trim().replace(/^♾️/u, "").toLowerCase();
    if (!/\.tp$/i.test(name)) name = `${name}.tp`;
    return name;
  };

  const go = () => {
    const raw = (ref.current?.value || "").trim();
    if (!raw) return;

    // First: always allow direct container ids / aliases regardless of toggle
    const guess = classifyAddress(raw);
    if (guess.kind === "container") {
      window.location.hash = `#/container/${encodeURIComponent(guess.target)}`;
      return;
    }

    // Respect the explicit mode for http vs wormhole
    if (mode === "http") {
      onNavigate({ mode: "http", address: ensureHttp(raw) });
      return;
    }

    // Wormhole mode
    onNavigate({ mode: "wormhole", address: normWormhole(raw) });
  };

  // QoL auto-switch:
  // - http(s)://… or www.… → http mode
  // - plain domain like example.com (but not *.tp) → http mode
  const handleChange = (v: string) => {
    const s = v.trim();
    if (/^https?:\/\//i.test(s) || s.startsWith("www.")) {
      if (mode !== "http") setMode("http");
      return;
    }
    if (/^[a-z0-9.-]+\.[a-z]{2,}$/i.test(s) && !/\.tp$/i.test(s)) {
      if (mode !== "http") setMode("http");
      return;
    }
  };

  return (
    <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
      {/* Mode toggle: ♾️ Multiverse | 🌐 Web */}
      <div
        role="group"
        aria-label="Address mode"
        style={{
          display: "inline-flex",
          border: "1px solid #e5e7eb",
          borderRadius: 999,
          overflow: "hidden",
          background: "#fff",
        }}
      >
        <button
          onClick={() => setMode("wormhole")}
          title="Multiverse (wormhole)"
          style={{
            minWidth: 38,
            padding: "6px 10px",
            border: "none",
            cursor: "pointer",
            background: mode === "wormhole" ? "#111827" : "transparent",
            color: mode === "wormhole" ? "#fff" : "#111827",
            fontWeight: 600,
          }}
        >
          ♾️
        </button>
        <button
          onClick={() => setMode("http")}
          title="Web (www)"
          style={{
            minWidth: 38,
            padding: "6px 10px",
            border: "none",
            cursor: "pointer",
            background: mode === "http" ? "#111827" : "transparent",
            color: mode === "http" ? "#fff" : "#111827",
            fontWeight: 600,
          }}
        >
          🌐
        </button>
      </div>

      {/* Address input */}
      <input
        ref={ref}
        placeholder={placeholder}
        onChange={(e) => handleChange(e.target.value)}
        onKeyDown={(e) => (e.key === "Enter" ? go() : undefined)}
        spellCheck={false}
        style={{
          flex: 1,
          minWidth: 0,
          padding: "8px 12px",
          borderRadius: 8,
          border: "1px solid #cbd5e1",
          outline: "none",
          background: "#fff",
        }}
      />

      <button
        onClick={go}
        style={{
          padding: "8px 14px",
          borderRadius: 8,
          background: "#0f172a",
          color: "#fff",
          border: "none",
          cursor: "pointer",
          fontWeight: 600,
        }}
      >
        Go
      </button>
    </div>
  );
}