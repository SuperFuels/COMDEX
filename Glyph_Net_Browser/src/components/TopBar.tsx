// src/components/TopBar.tsx
import React, { useEffect, useMemo, useRef, useState } from "react";
import WormholeBar from "./WormholeBar";

// SVG assets (from src/assets)
import tessarisLightLogo from "../assets/tessaris_light_logo.svg";
import tessarisDarkLogo from "../assets/tessaris_dark_logo.svg";

export type RadioStatus = "unknown" | "up" | "reconnecting" | "down";

type Props = {
  onNavigate: (
    s: string | { mode: "wormhole" | "http"; address: string },
  ) => void;
  onOpenSidebar: () => void;
  onAskAion: () => void; // still in props for now (button removed)
  onToggleWaves: () => void;
  wavesCount: number;
  radioStatus?: RadioStatus;

  // session-aware controls shown on right
  session?: { slug: string; wa: string; name?: string } | null;
  onLogout?: () => void;
};

type WalletSummary = {
  pho: string; // displayed PHO (same as WalletPanel big number)
  phoGlobal?: string; // raw on-chain PHO
  spendableLocal?: string; // offline spendable now
};

// 🔋 Small radio status pill (icon-only)
function RadioPill({ status = "unknown" as RadioStatus }) {
  const map = {
    up: {
      icon: "🛜",
      bg: "#bbf7d0",
      border: "#22c55e",
      label: "Radio: healthy",
    },
    reconnecting: {
      icon: "🛜",
      bg: "#fef3c7",
      border: "#f59e0b",
      label: "Radio: reconnecting…",
    },
    down: {
      icon: "🛜",
      bg: "#fee2e2",
      border: "#ef4444",
      label: "Radio: down",
    },
    unknown: {
      icon: "🛜",
      bg: "#e5e7eb",
      border: "#9ca3af",
      label: "Radio: unknown",
    },
  } as const;

  const cfg = map[status];

  return (
    <button
      type="button"
      title={cfg.label}
      style={{
        ...pill,
        padding: "6px 8px",
        background: cfg.bg,
        borderColor: cfg.border,
      }}
    >
      {cfg.icon}
    </button>
  );
}

// 🔵 BLE status pill (static for now)
function BlePill() {
  return (
    <button
      type="button"
      title="Bluetooth / mesh link"
      style={{
        ...pill,
        padding: "6px 8px",
        background: "#dbeafe",
        borderColor: "#3b82f6",
      }}
    >
      🌀
    </button>
  );
}

export default function TopBar(p: Props) {
  // Base URLs (optional)
  const websiteBase = (import.meta as any)?.env?.VITE_WEBSITE_BASE || "";
  const websiteApi = (import.meta as any)?.env?.VITE_WEBSITE_API || websiteBase;
  const radioBase =
    (import.meta as any)?.env?.VITE_RADIO_BASE || "http://127.0.0.1:8787";

  // 🌙 / ☀️ theme toggle (wiring real theming later)
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const tessLogoSrc = theme === "dark" ? tessarisDarkLogo : tessarisLightLogo;

  // Login dropdown state
  const [loginOpen, setLoginOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const loginWrapRef = useRef<HTMLDivElement>(null);

  // Wallet mini-pill state (kept for future use)
  const [walletSummary, setWalletSummary] = useState<WalletSummary | null>(
    null,
  );

  // Wallet summary for PHO pill
  const [walletPho, setWalletPho] = useState<string | null>(null);
  const [walletPhoLoading, setWalletPhoLoading] =
    useState<boolean>(false);

  async function refreshWalletSummary(waOverride?: string | null) {
    if (typeof window === "undefined") return;

    const wa =
      waOverride ??
      localStorage.getItem("gnet:ownerWa") ??
      localStorage.getItem("gnet:wa") ??
      null;

    setWalletPhoLoading(true);

    try {
      const resp = await fetch("/api/wallet/balances", {
        headers: wa ? { "X-Owner-WA": wa } : {},
      });
      const data = await resp.json();
      const b = data.balances || {};
      // Use the same displayed PHO that WalletPanel shows
      setWalletPho(b.pho ?? null);
    } catch (e) {
      console.warn("[TopBar] wallet summary failed:", e);
      setWalletPho(null);
    } finally {
      setWalletPhoLoading(false);
    }
  }

  useEffect(() => {
    if (typeof window === "undefined") return;

    // initial fetch
    void refreshWalletSummary();

    // listen for wallet changes from WalletPanel
    const handler = () => {
      void refreshWalletSummary();
    };
    window.addEventListener("glyphnet:wallet:updated", handler);
    return () =>
      window.removeEventListener("glyphnet:wallet:updated", handler);
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;

    async function loadWalletSummary() {
      try {
        const ownerWa =
          (p.session as any)?.wa ||
          localStorage.getItem("gnet:ownerWa") ||
          localStorage.getItem("gnet:wa") ||
          null;

        const resp = await fetch("/api/wallet/balances", {
          headers: ownerWa ? { "X-Owner-WA": ownerWa } : {},
        });
        if (!resp.ok) return;

        const data = await resp.json();
        const b = data.balances || {};

        setWalletSummary({
          pho: String(b.pho ?? "0.00"),
          phoGlobal:
            b.pho_global != null ? String(b.pho_global) : undefined,
          spendableLocal:
            b.pho_spendable_local != null
              ? String(b.pho_spendable_local)
              : undefined,
        });
      } catch (e) {
        console.warn("[TopBar] wallet summary failed:", e);
      }
    }

    // initial load
    void loadWalletSummary();

    // refresh when wallet panel broadcasts an update
    const handler = () => void loadWalletSummary();
    window.addEventListener("glyphnet:wallet:updated", handler);
    return () => window.removeEventListener("glyphnet:wallet:updated", handler);
  }, [p.session?.wa]);

  const profileLabel = useMemo(() => {
    if (!p.session) return "";
    if (p.session.name) return p.session.name;
    if (p.session.slug) return p.session.slug;
    return p.session.wa || "You";
  }, [p.session]);

  const goHome = () => {
    const slug = p.session?.slug || localStorage.getItem("gnet:user_slug");
    if (slug) window.location.hash = `#/container/${slug}__home`;
  };

  async function doLogin(e?: React.FormEvent) {
    e?.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      if (!websiteApi) {
        window.open(
          `${websiteBase || ""}/login`,
          "_blank",
          "noopener,noreferrer",
        );
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
      const slug = (data.slug || email.split("@")[0])
        .toLowerCase()
        .replace(/[^a-z0-9._-]/g, "-");
      const wa = data.wa || `${slug}@wave.tp`;

      await fetch(`${radioBase}/api/session/attach`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ slug, wa, token: data.token }),
      }).catch(() => {});

      // 3) Persist locally
      localStorage.setItem("gnet:user_slug", slug);
      localStorage.setItem("gnet:wa", wa);

      setLoginOpen(false);
      setEmail("");
      setPassword("");
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
      <button
        onClick={p.onOpenSidebar}
        aria-label="Open sidebar"
        title="Open sidebar"
        style={navBtn}
      >
        ☰
      </button>

      {/* Tessaris logo */}
      <img
        src={tessLogoSrc}
        alt="Tessaris"
        style={{
          height: 28,
          width: "auto",
          marginRight: 4,
        }}
      />

      {/* back / fwd / reload */}
      <button title="Back" style={navBtn} onClick={() => history.back()}>
        ◀
      </button>
      <button
        title="Forward"
        style={navBtn}
        onClick={() => history.forward()}
      >
        ▶
      </button>
      <button
        title="Reload"
        style={navBtn}
        onClick={() => location.reload()}
      >
        ⟳
      </button>

      {/* View toggle: 🌐 Web | 🌌 Multiverse */}
      <div role="group" aria-label="View mode" style={pillGroup}>
        <button
          title="Web"
          style={{ ...pillBtn, background: "#111827", color: "#fff" }}
          onClick={() => {
            // SPA stays; address bar navigates (no-op for now)
          }}
        >
          🌐
        </button>
        <button
          title="Multiverse"
          style={pillBtn}
          onClick={() => {
            const url = websiteBase
              ? `${websiteBase}/aion/multiverse`
              : "/aion/multiverse";
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
        {/* Radio + BLE icons */}
        <RadioPill status={p.radioStatus ?? "unknown"} />
        <BlePill />

        {/* Theme toggle – wiring real theming later */}
        <button
          type="button"
          onClick={() =>
            setTheme((t) => (t === "light" ? "dark" : "light"))
          }
          title={
            theme === "light"
              ? "Switch to dark mode"
              : "Switch to light mode"
          }
          style={{
            width: 34,
            height: 34,
            borderRadius: "999px",
            border: "1px solid #e5e7eb",
            background: "#fff",
            cursor: "pointer",
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 16,
          }}
        >
          {theme === "light" ? "🌙" : "☀️"}
        </button>

        {/* PHO mini pill */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 4,
            padding: "4px 10px",
            borderRadius: 999,
            border: "1px solid #e5e7eb",
            background: "#ffffff",
            fontSize: 11,
            color: "#4b5563",
            cursor: "default",
            whiteSpace: "nowrap",
          }}
          title="Displayed PHO ≈ on-chain PHO − mesh pending − 1 PHO safety buffer."
        >
          <span role="img" aria-label="PHO">
            💰
          </span>
          <span>{walletPhoLoading ? "…" : walletPho ?? "—"}</span>
          <span style={{ color: "#9ca3af" }}> PHO</span>
        </div>

        {/* Waves (no 'Waves' label, just glyph + count) */}
        <button style={pill} onClick={p.onToggleWaves}>
          🌊 {p.wavesCount ? `(${p.wavesCount})` : ""}
        </button>

        {/* Auth area */}
        {p.session ? (
          <>
            <button
              style={pill}
              onClick={goHome}
              title="Go to your Home container"
            >
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
            <button style={pill} onClick={p.onLogout}>
              🚪 Logout
            </button>
          </>
        ) : (
          <div ref={loginWrapRef} style={{ position: "relative" }}>
            <button
              style={pill}
              onClick={() => setLoginOpen((v) => !v)}
              title="Sign in"
            >
              🔐 Log in
            </button>

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
                <div style={{ fontWeight: 700, marginBottom: 8 }}>
                  Sign in
                </div>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  placeholder="Email"
                  style={input}
                />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  placeholder="Password"
                  style={{ ...input, marginTop: 8 }}
                />

                {/* Forgot password link */}
                <div style={{ marginTop: 6, textAlign: "right" }}>
                  <a
                    href={
                      websiteBase
                        ? `${websiteBase}/forgot-password`
                        : "#"
                    }
                    target="_blank"
                    rel="noreferrer"
                    style={{
                      fontSize: 12,
                      color: "#2563eb",
                      textDecoration: "underline",
                    }}
                    title="Reset your password"
                  >
                    Forgot password?
                  </a>
                </div>

                {err && (
                  <div
                    style={{
                      color: "#b91c1c",
                      fontSize: 12,
                      marginTop: 6,
                    }}
                  >
                    {err}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={busy}
                  style={{ ...btnPrimary, marginTop: 10 }}
                >
                  {busy ? "Signing in…" : "Sign in"}
                </button>

                {/* Inline sign-up link (moved from top bar) */}
                <div
                  style={{
                    marginTop: 8,
                    fontSize: 12,
                    textAlign: "center",
                    color: "#4b5563",
                  }}
                >
                  New here?{" "}
                  <a
                    href={
                      websiteBase ? `${websiteBase}/register` : "#"
                    }
                    target="_blank"
                    rel="noreferrer"
                    style={{
                      color: "#2563eb",
                      textDecoration: "underline",
                    }}
                  >
                    Create an account
                  </a>
                </div>
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
  border: "1px solid #e5e7eb",  // 👈 was `"1px solid "#e5e7eb"`
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