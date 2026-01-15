"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { DarkModeToggle } from "@/components/DarkModeToggle";

type RadioStatus = "unknown" | "up" | "reconnecting" | "down";

type Session = { slug: string; wa: string; name?: string } | null;

function RadioPill({ status = "unknown" }: { status?: RadioStatus }) {
  const cfg =
    status === "up"
      ? { bg: "bg-emerald-200", border: "border-emerald-500", title: "Radio: healthy" }
      : status === "reconnecting"
      ? { bg: "bg-amber-200", border: "border-amber-500", title: "Radio: reconnecting…" }
      : status === "down"
      ? { bg: "bg-red-200", border: "border-red-500", title: "Radio: down" }
      : { bg: "bg-gray-200", border: "border-gray-400", title: "Radio: unknown" };

  return (
    <button
      type="button"
      title={cfg.title}
      className={`h-9 w-9 rounded-full border ${cfg.border} ${cfg.bg} grid place-items-center`}
    >
      🛜
    </button>
  );
}

function BlePill() {
  return (
    <button
      type="button"
      title="Bluetooth / mesh link"
      className="h-9 w-9 rounded-full border border-blue-500 bg-blue-100 grid place-items-center"
    >
      🌀
    </button>
  );
}

function ViewToggle() {
  return (
    <div className="inline-flex overflow-hidden rounded-full border border-border bg-background/80">
      <button
        type="button"
        title="Web"
        className="px-3 py-1 text-sm bg-button-light/60 dark:bg-button-dark/70 text-text hover:bg-button-light/70 dark:hover:bg-button-dark/80"
        onClick={() => {
          // no-op: you are already in the web shell
        }}
      >
        🌐
      </button>
      <button
        type="button"
        title="Multiverse"
        className="px-3 py-1 text-sm border-l border-border text-text/80 hover:bg-button-light/70 dark:hover:bg-button-dark/80"
        onClick={() => {
          window.open("/aion/multiverse", "_blank", "noopener,noreferrer");
        }}
      >
        🌌
      </button>
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

        // very lightweight behavior:
        // - http(s) opens a new tab
        // - "#/path" sets hash router path
        // - otherwise treat as a search-ish token -> devtools for now
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

export default function GlyphNetNavbar({
  onOpenSidebar,
}: {
  onOpenSidebar?: () => void;
}) {
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
      const wa =
        localStorage.getItem("gnet:ownerWa") ??
        localStorage.getItem("gnet:wa") ??
        null;

      setPhoLoading(true);
      try {
        const resp = await fetch("/api/wallet/balances", {
          headers: wa ? { "X-Owner-WA": wa } : {},
        });
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
      // Minimal “keep it working” login:
      // If you have a website API, wire it via env and do the real call here.
      // Otherwise we create a local session so GlyphNet controls can use WA headers.
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
      {/* Sidebar toggle (match your main Navbar: fixed, G icon) */}
      {onOpenSidebar && (
        <button
          onClick={onOpenSidebar}
          className="fixed top-4 left-4 z-50 rounded-lg border border-border bg-background px-2 py-2"
          aria-label="Open menu"
        >
          <Image src="/G.svg" alt="Menu" width={32} height={32} />
        </button>
      )}

      {/* Sticky header shell (same borders/colors vibe as your main Navbar) */}
      <header className="sticky top-0 z-40 border-b border-border bg-background text-text">
        <div className="flex h-16 items-center justify-between gap-4 px-4">
          {/* Logo (keep your Tessaris logos) */}
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

          {/* Center: view toggle + address bar (replaces swap strip) */}
          <div className="flex flex-1 items-center justify-center gap-3">
            <ViewToggle />
            <div className="w-[min(720px,60vw)]">
              <AddressBar />
            </div>
          </div>

          {/* Right controls: radio/ble/theme/PHO/waves/login (replaces connect wallet) */}
          <div className="flex items-center gap-3">
            <RadioPill status="unknown" />
            <BlePill />

            <DarkModeToggle />

            {/* PHO mini pill */}
            <div
              className="hidden sm:flex items-center gap-2 rounded-full border border-border bg-background px-3 py-1 text-xs text-text/80"
              title="Displayed PHO (from /api/wallet/balances)"
            >
              <span>💰</span>
              <span>{phoLoading ? "…" : pho ?? "—"}</span>
              <span className="text-text/50">PHO</span>
            </div>

            {/* Waves (stub action for now) */}
            <button
              className="rounded-lg border border-border bg-transparent px-3 py-1 text-sm text-text hover:bg-button-light/50 dark:hover:bg-button-dark/50"
              onClick={() => (window.location.hash = "#/devtools")}
              title="Waves"
            >
              🌊
            </button>

            {/* Auth */}
            {session ? (
              <>
                <button
                  className="rounded-lg border border-border bg-transparent px-3 py-1 text-sm text-text hover:bg-button-light/50 dark:hover:bg-button-dark/50"
                  onClick={() => (window.location.hash = "#/devtools")}
                  title="Profile / Home container"
                >
                  {profileLabel}
                </button>
                <button
                  className="rounded-lg border border-border bg-transparent px-3 py-1 text-sm text-text hover:bg-button-light/50 dark:hover:bg-button-dark/50"
                  onClick={doLogout}
                >
                  Logout
                </button>
              </>
            ) : (
              <div ref={wrapRef} className="relative">
                <button
                  className="rounded-lg border border-border bg-transparent px-3 py-1 text-sm text-text hover:bg-button-light/50 dark:hover:bg-button-dark/50"
                  onClick={() => setLoginOpen((v) => !v)}
                >
                  Log in
                </button>

                {loginOpen && (
                  <form className="absolute right-0 mt-2 w-72 rounded-lg border border-border bg-background p-3 shadow-lg" onSubmit={doLogin}>
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