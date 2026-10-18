"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import Image from "next/image";
import Link from "next/link";

type RadioStatus = "unknown" | "up" | "reconnecting" | "down";
type Session = { slug: string; wa: string; name?: string } | null;

// ✅ unified navbar icon button: uses .navbar-icon-btn to opt out of global button borders/padding
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
        "navbar-icon-btn", // ✅ IMPORTANT: kills global button border/padding
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
        🪐
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

export default function GlyphNetNavbar({
  onOpenSidebar,
}: {
  onOpenSidebar?: () => void; // optional now (no fixed hamburger)
}) {
  const [session, setSession] = useState<Session>(null);

  const [pho, setPho] = useState<string | null>(null);
  const [phoLoading, setPhoLoading] = useState(false);

  // ✅ Login UI is back (and disappears once logged in)
  const [loginOpen, setLoginOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const wrapRef = useRef<HTMLDivElement>(null);

  const profileLabel = useMemo(() => {
    if (!session) return "";
    return session.name || session.slug || session.wa || "You";
  }, [session]);

  // close dropdown on outside click
  useEffect(() => {
    function onDown(e: MouseEvent) {
      if (loginOpen && wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setLoginOpen(false);
      }
    }
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [loginOpen]);

  // Session bootstrap comes from the HttpOnly-cookie authority. Identity is
  // kept in this process only, never reconstructed from browser storage.
  useEffect(() => {
    if (typeof window === "undefined") return;

    const read = async (event?: Event) => {
      const detail = (event as CustomEvent<Session> | undefined)?.detail;
      if (detail?.slug && detail?.wa) {
        setSession(detail);
        return;
      }
      try {
        const response = await fetch("/auth/profile", { credentials: "include" });
        if (!response.ok) throw new Error("No active session");
        const profile = await response.json();
        const slug = String(profile.email || profile.name || "user")
          .split("@")[0]
          .toLowerCase()
          .replace(/[^a-z0-9._-]/g, "-");
        setSession({ slug, wa: `${slug}@wave.tp`, name: profile.name });
      } catch {
        setSession(null);
      }
    };

    void read();
    const handler = (event: Event) => void read(event);
    window.addEventListener("gnet:session:changed", handler);
    return () => window.removeEventListener("gnet:session:changed", handler);
  }, []);

  // PHO pill
  useEffect(() => {
    if (typeof window === "undefined") return;

    const refresh = async () => {
      const wa = session?.wa ?? null;

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
  }, [session?.wa]);

  const doLogout = async () => {
    if (typeof window === "undefined") return;
    try {
      await fetch("/auth/logout", { method: "POST", credentials: "include" });
    } catch {
      // The local view is still cleared if the authority is unavailable.
    }
    setSession(null);
    setLoginOpen(false);
    window.dispatchEvent(new CustomEvent("gnet:session:changed"));
  };

  async function doLogin(e?: React.FormEvent) {
    e?.preventDefault();
    setBusy(true);
    setErr(null);

    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!response.ok) throw new Error("Login failed");
      const slug = (email.split("@")[0] || "user")
        .toLowerCase()
        .replace(/[^a-z0-9._-]/g, "-");
      const wa = `${slug}@wave.tp`;

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
      {/* ✅ no fixed G button, no fixed hamburger; sidebar owns the G toggle now */}

      <header className="sticky top-0 z-40 border-b border-[#e5e7eb] bg-background text-text">
        <div className="flex h-16 items-center justify-between gap-4 px-4">
          {/* Logo */}
          <div className="flex items-center">
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

          {/* Right controls */}
          <div className="flex items-center gap-2">
            <RadioPill status="unknown" />
            <BlePill />

            <div
              className="hidden sm:flex items-center gap-2 rounded-full bg-transparent px-3 py-1 text-xs text-text/80"
              title="Displayed PHO (from /api/wallet/balances)"
            >
              <span className="text-base">💰</span>
              <span>{phoLoading ? "…" : pho ?? "—"}</span>
              <span className="text-text/50">PHO</span>
            </div>

            <IconBtn title="Waves" onClick={() => (window.location.hash = "#/devtools")}>
              🌊
            </IconBtn>

            {/* ✅ Login button returns, but disappears once logged in */}
            {session ? (
              <div className="hidden md:flex items-center gap-2 rounded-full bg-transparent px-2 py-1 text-xs text-text/70">
                <span className="text-text/50">Signed in:</span>
                <span className="text-text" title={session.wa}>
                  {profileLabel}
                </span>
                <button
                  onClick={doLogout}
                  className="navbar-icon-btn ml-1 h-8 w-8 rounded-full grid place-items-center hover:bg-button-light/30 dark:hover:bg-button-dark/30 text-text/70"
                  title="Logout"
                  type="button"
                >
                  <span className="text-lg leading-none">⎋</span>
                </button>
              </div>
            ) : (
              <div ref={wrapRef} className="relative">
                <button
                  type="button"
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
