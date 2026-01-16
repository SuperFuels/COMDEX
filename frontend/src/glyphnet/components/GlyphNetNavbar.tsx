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

export default function GlyphNetNavbar({
  onOpenSidebar,
}: {
  onOpenSidebar?: () => void; // optional now (no fixed hamburger)
}) {
  const [session, setSession] = useState<Session>(null);

  const [pho, setPho] = useState<string | null>(null);
  const [phoLoading, setPhoLoading] = useState(false);

  // retained (for sidebar integration soon) — but no Login UI in navbar
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

  // close dropdown on outside click (kept for later sidebar move)
  useEffect(() => {
    function onDown(e: MouseEvent) {
      if (loginOpen && wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setLoginOpen(false);
      }
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

  // kept for later (sidebar auth)
  const doLogout = () => {
    if (typeof window === "undefined") return;
    localStorage.removeItem("gnet:user_slug");
    localStorage.removeItem("gnet:wa");
    localStorage.removeItem("gnet:ownerWa");
    setSession(null);
    window.dispatchEvent(new CustomEvent("gnet:session:changed"));
  };

  // kept for later (sidebar auth)
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
      {/* ✅ no fixed G button, no fixed hamburger; sidebar owns the G toggle now */}

      {/* Sticky header shell (light grey border) */}
      <header className="sticky top-0 z-40 border-b border-[#e5e7eb] bg-background text-text">
        <div className="flex h-16 items-center justify-between gap-4 px-4">
          {/* ✅ Logo moved slightly left (no extra left margin) */}
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

          {/* Right controls (NO borders, NO darkmode toggle, NO login button) */}
          <div className="flex items-center gap-2">
            <RadioPill status="unknown" />
            <BlePill />

            {/* PHO mini pill: keep text, no border */}
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

            {/* ✅ retain session info display, but remove login UI */}
            {session ? (
              <div
                className="hidden md:flex items-center gap-2 rounded-full bg-transparent px-3 py-1 text-xs text-text/70"
                title={session.wa}
              >
                <span className="text-text/50">Signed in:</span>
                <span className="text-text">{profileLabel}</span>
                {/* optional: keep logout callable but unobtrusive */}
                <button
                  onClick={doLogout}
                  className="ml-2 rounded-full px-2 py-1 hover:bg-button-light/30 dark:hover:bg-button-dark/30 text-text/70"
                  title="Logout"
                  type="button"
                >
                  ⎋
                </button>
              </div>
            ) : (
              <div className="hidden md:flex items-center rounded-full bg-transparent px-3 py-1 text-xs text-text/50">
                Not signed in
              </div>
            )}
          </div>
        </div>
      </header>

      {/* NOTE: loginOpen/email/password/busy/err/doLogin kept for sidebar migration; navbar renders none */}
      <div className="hidden">
        <div ref={wrapRef} />
        <button onClick={() => setLoginOpen(false)} type="button" />
        <form onSubmit={doLogin} />
        <input value={email} readOnly />
        <input value={password} readOnly />
        <span>{busy ? "1" : "0"}</span>
        <span>{err ?? ""}</span>
      </div>
    </>
  );
}