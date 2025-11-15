// src/components/TopBar.tsx
import React, { useEffect, useMemo, useRef, useState } from "react";
import WormholeBar from "./WormholeBar";

export type RadioStatus = "unknown" | "up" | "reconnecting" | "down";

type Props = {
  onNavigate: (s: string | { mode: "wormhole" | "http"; address: string }) => void;
  onOpenSidebar: () => void;
  onAskAion: () => void;
  onToggleWaves: () => void;
  wavesCount: number;
  radioStatus?: RadioStatus;

  // session-aware controls shown on right
  session?: { slug: string; wa: string; name?: string } | null;
  onLogout?: () => void;
};

function HealthPill({ status = "unknown" as RadioStatus }) {
  const map = {
    up:           { dot: "#16a34a", text: "Radio: healthy",       bg: "#e6f7ed", fg: "#065f46" },
    reconnecting: { dot: "#f59e0b", text: "Radio: reconnecting…", bg: "#fff7ed", fg: "#92400e" },
    down:         { dot: "#ef4444", text: "Radio: down",          bg: "#fee2e2", fg: "#991b1b" },
    unknown:      { dot: "#9ca3af", text: "Radio: unknown",       bg: "#f3f4f6", fg: "#374151" },
  } as const;
  const s = map[status];
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 8,
        padding: "4px 10px",
        borderRadius: 999,
        background: s.bg,
        color: s.fg,
        fontSize: 12,
        fontWeight: 600,
        border: "1px solid rgba(0,0,0,0.06)",
        whiteSpace: "nowrap",
      }}
      title={s.text}
    >
      <span
        style={{
          width: 8,
          height: 8,
          borderRadius: 999,
          background: s.dot,
          boxShadow: `0 0 0 2px ${s.dot}22`,
        }}
      />
      {s.text}
    </span>
  );
}

export default function TopBar(p: Props) {
  // Base URLs (optional)
  const websiteBase = (import.meta as any)?.env?.VITE_WEBSITE_BASE || "";
  const websiteApi  = (import.meta as any)?.env?.VITE_WEBSITE_API  || websiteBase;
  const radioBase   = (import.meta as any)?.env?.VITE_RADIO_BASE   || "http://127.0.0.1:8787";

  // Login dropdown state
  const [loginOpen, setLoginOpen] = useState(false);
  const [email, setEmail]         = useState("");
  const [password, setPassword]   = useState("");
  const [busy, setBusy]           = useState(false);
  const [err, setErr]             = useState<string | null>(null);
  const loginWrapRef              = useRef<HTMLDivElement>(null);

  // close login dropdown on outside click
  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (!loginOpen) return;
      if (loginWrapRef.current && !loginWrapRef.current.contains(e.target as Node)) {
        setLoginOpen(false);
      }
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [loginOpen]);

  const profileLabel = useMemo(() => {
    if (!p.session) return "";
    if (p.session.name) return p.session.name;
    if (p.session.slug) return p.session.slug;
    return p.session.wa || "You";
  }, [p.session]);

  const gotoBridge = () => { window.location.hash = "#/bridge"; };
  const goHome = () => {
    const slug = p.session?.slug || localStorage.getItem("gnet:user_slug");
    if (slug) window.location.hash = `#/container/${slug}__home`;
  };

  async function doLogin(e?: React.FormEvent) {
    e?.preventDefault();
    setBusy(true); setErr(null);
    try {
      if (!websiteApi) {
        window.open(`${websiteBase || ""}/login`, "_blank", "noopener,noreferrer");
        setBusy(false);
        return;
      }

      // 1) Login to website backend
      const res = await fetch(`${websiteApi}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) throw new Error((await res.text()) || "Login failed");
      const data = await res.json(); // { token, role, slug?, wa? }

      // 2) Attach to local radio runtime
      const slug = (data.slug || email.split("@")[0]).toLowerCase().replace(/[^a-z0-9._-]/g, "-");
      const wa   = data.wa || `${slug}@wave.tp`;

      await fetch(`${radioBase}/api/session/attach`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ slug, wa, token: data.token }),
      }).catch(() => {});

      // 3) Persist locally
      localStorage.setItem("gnet:user_slug", slug);
      localStorage.setItem("gnet:wa", wa);

      setLoginOpen(false);
      setEmail(""); setPassword("");
      window.dispatchEvent(new CustomEvent("gnet:session:changed"));
    } catch (e: any) {
      setErr(e?.message || "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <header
      style={{
        height: 56,
        display: "flex",
        alignItems: "center",
        gap: 8,
        padding: "8px 12px",
        borderBottom: "1px solid #e5e7eb",
        background: "#fff",
        position: "sticky",
        top: 0,
        zIndex: 38,
      }}
    >
      {/* hamburger */}
      <button onClick={p.onOpenSidebar} aria-label="Open sidebar" title="Open sidebar" style={navBtn}>☰</button>

      {/* back / fwd / reload */}
      <button title="Back" style={navBtn} onClick={() => history.back()}>◀</button>
      <button title="Forward" style={navBtn} onClick={() => history.forward()}>▶</button>
      <button title="Reload" style={navBtn} onClick={() => location.reload()}>⟳</button>

      {/* View toggle: 🌐 Web | 🌌 Multiverse */}
      <div role="group" aria-label="View mode" style={pillGroup}>
        <button
          title="Web"
          style={{ ...pillBtn, background: "#111827", color: "#fff" }}
          onClick={() => { /* SPA stays; address bar navigates */ }}
        >
          🌐
        </button>
        <button
          title="Multiverse"
          style={pillBtn}
          onClick={() => {
            const url = websiteBase ? `${websiteBase}/aion/multiverse` : "/aion/multiverse";
            window.open(url, "_blank", "noopener,noreferrer");
          }}
        >
          🌌
        </button>
      </div>

      {/* address bar */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <WormholeBar onNavigate={p.onNavigate} />
      </div>

      {/* Right controls */}
      <div style={{ display: "inline-flex", gap: 8, alignItems: "center" }}>
        <HealthPill status={p.radioStatus ?? "unknown"} />
        <button style={pill} onClick={gotoBridge} title="Open RF Bridge panel">📡 Bridge</button>
        <button style={pill} onClick={p.onAskAion}>🫖 Ask AION</button>
        <button style={pill} onClick={p.onToggleWaves}>
          🌊 Waves {p.wavesCount ? `(${p.wavesCount})` : ""}
        </button>

        {/* Auth area */}
        {p.session ? (
          <>
            <button style={pill} onClick={goHome} title="Go to your Home container">
              <span
                style={{
                  display: "inline-block",
                  width: 8,
                  height: 8,
                  borderRadius: 999,
                  background: "#16a34a",
                  boxShadow: "0 0 0 2px #16a34a22",
                  marginRight: 6,
                }}
              />
              {profileLabel}
            </button>
            <button style={pill} onClick={p.onLogout}>🚪 Logout</button>
          </>
        ) : (
          <div ref={loginWrapRef} style={{ position: "relative" }}>
            <button style={pill} onClick={() => setLoginOpen(v => !v)} title="Sign in">🔐 Log in</button>
            <a
              style={pill}
              href={websiteBase ? `${websiteBase}/register` : "#"}
              target="_blank"
              rel="noreferrer"
              title="Open register"
            >
              ✨ Sign up
            </a>

            {/* dropdown login */}
            {loginOpen && (
              <form
                onSubmit={doLogin}
                style={{
                  position: "absolute",
                  right: 0,
                  marginTop: 8,
                  width: 280,
                  background: "#fff",
                  border: "1px solid #e5e7eb",
                  borderRadius: 12,
                  boxShadow: "0 10px 30px rgba(0,0,0,.12)",
                  padding: 12,
                  zIndex: 100,
                }}
              >
                <div style={{ fontWeight: 700, marginBottom: 8 }}>Sign in</div>
                <input
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  required
                  placeholder="Email"
                  style={input}
                />
                <input
                  type="password"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  required
                  placeholder="Password"
                  style={{ ...input, marginTop: 8 }}
                />

                {/* Forgot password link */}
                <div style={{ marginTop: 6, textAlign: "right" }}>
                  <a
                    href={websiteBase ? `${websiteBase}/forgot-password` : "#"}
                    target="_blank"
                    rel="noreferrer"
                    style={{ fontSize: 12, color: "#2563eb", textDecoration: "underline" }}
                    title="Reset your password"
                  >
                    Forgot password?
                  </a>
                </div>

                {err && <div style={{ color: "#b91c1c", fontSize: 12, marginTop: 6 }}>{err}</div>}
                <button type="submit" disabled={busy} style={{ ...btnPrimary, marginTop: 10 }}>
                  {busy ? "Signing in…" : "Sign in"}
                </button>
              </form>
            )}
          </div>
        )}
      </div>
    </header>
  );
}

/* ——— Styles ——— */
const navBtn: React.CSSProperties = {
  width: 34,
  height: 34,
  borderRadius: 8,
  border: "1px solid #e5e7eb",
  background: "#fff",
  cursor: "pointer",
};

const pill: React.CSSProperties = {
  borderRadius: 12,
  padding: "6px 10px",
  border: "1px solid #e5e7eb",
  background: "#fff",
  cursor: "pointer",
};

const pillGroup: React.CSSProperties = {
  display: "inline-flex",
  border: "1px solid #e5e7eb",
  borderRadius: 999,
  overflow: "hidden",
  background: "#fff",
  marginRight: 8,
};

const pillBtn: React.CSSProperties = {
  padding: "6px 10px",
  border: "none",
  cursor: "pointer",
  background: "transparent",
  color: "#111827",
  fontWeight: 700,
  minWidth: 40,
};

const input: React.CSSProperties = {
  width: "100%",
  padding: "8px 10px",
  borderRadius: 8,
  border: "1px solid #e5e7eb",
  outline: "none",
};

const btnPrimary: React.CSSProperties = {
  width: "100%",
  padding: "8px 10px",
  borderRadius: 8,
  background: "#111827",
  color: "#fff",
  border: "none",
  cursor: "pointer",
  fontWeight: 700,
};