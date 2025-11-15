import React from "react";

const siteBase =
  (import.meta as any)?.env?.VITE_WEBSITE_BASE ||
  // TODO: put your real website URL here if you want a hard default:
  "https://your-site.vercel.app";

export default function LoginPrompt({ onRefresh }: { onRefresh: () => void }) {
  return (
    <div
      style={{
        padding: 12,
        border: "1px solid #e5e7eb",
        borderRadius: 8,
        background: "#fff",
        display: "flex",
        alignItems: "center",
        gap: 12,
        justifyContent: "space-between",
      }}
    >
      <div>
        <strong>Welcome.</strong> Sign in to load your containers and waves.
      </div>
      <div style={{ display: "flex", gap: 8 }}>
        <a
          href={`${siteBase}/login`}
          target="_blank"
          rel="noreferrer"
          style={btn}
          title="Open website login in a new tab"
        >
          🔐 Sign in
        </a>
        <a
          href={`${siteBase}/register`}
          target="_blank"
          rel="noreferrer"
          style={btn}
          title="Open website register in a new tab"
        >
          ✨ Register
        </a>
        <button onClick={onRefresh} style={btn} title="I’ve signed in — refresh now">
          ↻ I’ve signed in
        </button>
      </div>
    </div>
  );
}

const btn: React.CSSProperties = {
  borderRadius: 10,
  padding: "8px 12px",
  border: "1px solid #e5e7eb",
  background: "#f9fafb",
  cursor: "pointer",
  textDecoration: "none",
  color: "#111827",
  fontWeight: 600,
};