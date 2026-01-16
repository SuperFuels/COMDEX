"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import Image from "next/image";
import Link from "next/link";

type RadioStatus = "unknown" | "up" | "reconnecting" | "down";
type Session = { slug: string; wa: string; name?: string } | null;

// ✅ unified icon button: NO BORDER, transparent, centered, uniform size
function IconBtn({
  title,
  onClick,
  children,
}: {
  title: string;
  onClick?: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      title={title}
      onClick={onClick}
      className={[
        "h-11 w-11 rounded-full",
        "grid place-items-center",
        "bg-transparent",
        "hover:bg-button-light/30 dark:hover:bg-button-dark/30",
        "focus:outline-none focus:ring-2 focus:ring-ring/30",
      ].join(" ")}
    >
      <span className="text-2xl leading-none">{children}</span>
    </button>
  );
}

function RadioPill({ status = "unknown" }: { status?: RadioStatus }) {
  const title =
    status === "up"
      ? "Radio: healthy"
      : status === "reconnecting"
      ? "Radio: reconnecting…"
      : status === "down"
      ? "Radio: down"
      : "Radio: unknown";

  return <IconBtn title={title}>🛜</IconBtn>;
}

function BlePill() {
  return <IconBtn title="Bluetooth / mesh link">🌀</IconBtn>;
}

function ViewToggle() {
  return (
    <div className="flex items-center gap-2">
      <IconBtn title="Web">🌐</IconBtn>
      <IconBtn
        title="Multiverse"
        onClick={() => window.open("/aion/multiverse", "_blank", "noopener,noreferrer")}
      >
        🌌
      </IconBtn>
    </div>
  );
}

function AddressBar() {
  const [v, setV] = useState("");

  return (
    <form
      className="flex w-full items-center gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        const s = v.trim();
        if (!s) return;

        if (/^https?:\/\//i.test(s)) {
          window.open(s, "_blank", "noopener,noreferrer");
          return;
        }
        if (s.startsWith("#/")) {
          window.location.hash = s;
          return;
        }
        window.location.hash = `#/devtools?query=${encodeURIComponent(s)}`;
      }}
    >
      <input
        value={v}
        onChange={(e) => setV(e.target.value)}
        placeholder="Wormhole / URL / query…"
        className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-text focus:outline-none focus:ring-2 focus:ring-ring/30"
      />
    </form>
  );
}

export default function GlyphNetNavbar({ onOpenSidebar }: { onOpenSidebar: () => void }) {
  const [session, setSession] = useState<Session>(null);
  const [loginOpen, setLoginOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const [pho, setPho] = useState<string | null>(null);
  const [phoLoading, setPhoLoading] = useState(false);

  const wrapRef = useRef<HTMLDivElement>(null);

  const profileLabel = useMemo(() => {
    if (!session) return "";
    return session.name || session.slug || session.wa || "You";
  }, [session]);

  // close dropdown on outside click
  useEffect(() => {
    function onDown(e: MouseEvent) {
      if (loginOpen && wrapRef.current && !wrapRef.current.contains(e.target as Node)) setLoginOpen(false);
    }
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [loginOpen]);

  // session bootstrap
  useEffect(() => {
    if (typeof window === "undefined") return;

    const read = () => {
      const slug = localStorage.getItem("gnet:user_slug");
      const wa = localStorage.getItem("gnet:wa") || localStorage.getItem("gnet:ownerWa");
      if (slug && wa) setSession({ slug, wa });
      else setSession(null);
    };

    read();
    const handler = () => read();
    window.addEventListener("gnet:session:changed", handler);
    return () => window.removeEventListener("gnet:session:changed", handler);
  }, []);

  // PHO pill
  useEffect(() => {
    if (typeof window === "undefined") return;

    const refresh = async () => {
      const wa = localStorage.getItem("gnet:ownerWa") ?? localStorage.getItem("gnet:wa") ?? null;

      setPhoLoading(true);
      try {
        const resp = await fetch("/api/wallet/balances", { headers: wa ? { "X-Owner-WA": wa } : {} });
        const data = await resp.json().catch(() => ({}));
        const b = data?.balances || {};
        setPho(b?.pho ?? null);
      } catch {
        setPho(null);
      } finally {
        setPhoLoading(false);
      }
    };

    void refresh();
    const h = () => void refresh();
    window.addEventListener("glyphnet:wallet:updated", h);
    return () => window.removeEventListener("glyphnet:wallet:updated", h);
  }, []);

  const doLogout = () => {
    if (typeof window === "undefined") return;
    localStorage.removeItem("gnet:user_slug");
    localStorage.removeItem("gnet:wa");
    localStorage.removeItem("gnet:ownerWa");
    setSession(null);
    window.dispatchEvent(new CustomEvent("gnet:session:changed"));
  };

  async function doLogin(e?: React.FormEvent) {
    e?.preventDefault();
    setBusy(true);
    setErr(null);

    try {
      const slug = (email.split("@")[0] || "user").toLowerCase().replace(/[^a-z0-9._-]/g, "-");
      const wa = `${slug}@wave.tp`;

      localStorage.setItem("gnet:user_slug", slug);
      localStorage.setItem("gnet:wa", wa);

      setLoginOpen(false);
      setEmail("");
      setPassword("");
      setSession({ slug, wa });
      window.dispatchEvent(new CustomEvent("gnet:session:changed"));
    } catch (e: any) {
      setErr(e?.message || "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      {/* Sidebar trigger (NOT the G icon; sidebar owns G now) */}
      <button
        onClick={onOpenSidebar}
        className="fixed top-4 left-4 z-50 h-11 w-11 rounded-xl bg-transparent grid place-items-center hover:bg-button-light/30 dark:hover:bg-button-dark/30"
        aria-label="Open sidebar"
        title="Open sidebar"
      >
        <span className="text-2xl leading-none">☰</span>
      </button>

      {/* Sticky header shell (light grey border) */}
      <header className="sticky top-0 z-40 border-b border-[#e5e7eb] bg-background text-text">
        <div className="flex h-16 items-center justify-between gap-4 px-4">
          {/* Logo */}
          <div className="ml-12 flex items-center">
            <Link href="/" className="logo-link flex items-center">
              <Image
                src="/tessaris_light_logo.svg"
                alt="Tessaris"
                width={166}
                height={52}
                priority
                className="block dark:hidden border-none"
              />
              <Image
                src="/tessaris_dark_logo.svg"
                alt="Tessaris"
                width={166}
                height={52}
                priority
                className="hidden dark:block border-none"
              />
            </Link>
          </div>

          {/* Center */}
          <div className="flex flex-1 items-center justify-center gap-4">
            <ViewToggle />
            <div className="w-[min(720px,60vw)]">
              <AddressBar />
            </div>
          </div>

          {/* Right controls (NO borders, NO darkmode toggle) */}
          <div className="flex items-center gap-2">
            <RadioPill status="unknown" />
            <BlePill />

            {/* PHO mini pill: keep text, border removed */}
            <div
              className="hidden sm:flex items-center gap-2 rounded-full bg-transparent px-3 py-1 text-xs text-text/80"
              title="Displayed PHO (from /api/wallet/balances)"
            >
              <span className="text-base">💰</span>
              <span>{phoLoading ? "…" : pho ?? "—"}</span>
              <span className="text-text/50">PHO</span>
            </div>

            {/* Waves inbox: NO border */}
            <IconBtn
              title="Waves"
              onClick={() => {
                window.location.hash = "#/devtools";
              }}
            >
              🌊
            </IconBtn>

            {/* Auth */}
            {session ? (
              <>
                <button
                  className="rounded-lg bg-transparent px-3 py-2 text-sm text-text hover:bg-button-light/30 dark:hover:bg-button-dark/30"
                  onClick={() => (window.location.hash = "#/devtools")}
                  title="Profile / Home container"
                >
                  {profileLabel}
                </button>
                <button
                  className="rounded-lg bg-transparent px-3 py-2 text-sm text-text hover:bg-button-light/30 dark:hover:bg-button-dark/30"
                  onClick={doLogout}
                >
                  Logout
                </button>
              </>
            ) : (
              <div ref={wrapRef} className="relative">
                <button
                  className="rounded-lg bg-transparent px-3 py-2 text-sm text-text hover:bg-button-light/30 dark:hover:bg-button-dark/30"
                  onClick={() => setLoginOpen((v) => !v)}
                >
                  Log in
                </button>

                {loginOpen && (
                  <form
                    className="absolute right-0 mt-2 w-72 rounded-lg border border-[#e5e7eb] bg-background p-3 shadow-lg"
                    onSubmit={doLogin}
                  >
                    <div className="mb-2 text-sm font-semibold">Sign in</div>

                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                      placeholder="Email"
                      className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                    />
                    <input
                      type="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      placeholder="Password"
                      className="mt-2 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                    />

                    {err && <div className="mt-2 text-xs text-red-500">{err}</div>}

                    <button
                      type="submit"
                      disabled={busy}
                      className="mt-3 w-full rounded-lg border border-border bg-button-light/60 dark:bg-button-dark/70 px-3 py-2 text-sm hover:bg-button-light/70 dark:hover:bg-button-dark/80"
                    >
                      {busy ? "Signing in…" : "Sign in"}
                    </button>
                  </form>
                )}
              </div>
            )}
          </div>
        </div>
      </header>
    </>
  );
}