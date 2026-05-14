"use client";

import React from "react";

/**
 * frontend/tabs/Aion/demos/ui.tsx
 * Light-mode “SLE / RQC HUD” branding + DARK data-surface for live feeds
 * - page bg handled in AionProofOfLifeDashboard.tsx
 * - these atoms are neutral + clean, with Tessaris blue as accent
 * - includes: dark tiles (for unreadable left panels), API/WS base helpers, freshness helpers
 */

export const TESSARIS_COLORS = {
  blue: "#1B74E4", // tessarisBlue
  ink: "#0F172A", // tessarisInk
  slate: "#64748B", // tessarisGray
  emerald: "#10B981", // tessarisGreen
  amber: "#F59E0B", // tessarisAmber
  rose: "#EF4444", // tessarisRed
};

export function classNames(...xs: Array<string | false | null | undefined>) {
  return xs.filter(Boolean).join(" ");
}

export function clamp01(x: number) {
  if (!Number.isFinite(x)) return 0;
  return Math.max(0, Math.min(1, x));
}

export function fmt2(x?: number | null) {
  if (x === null || x === undefined || Number.isNaN(x)) return "—";
  return x.toFixed(2);
}

export function fmt3(x?: number | null) {
  if (x === null || x === undefined || Number.isNaN(x)) return "—";
  return x.toFixed(3);
}

/**
 * ✅ Needed by demo01_metabolism.tsx
 * Accepts: seconds, ms, ISO string, numeric string, Date.
 * Returns age in ms (clamped >= 0) or null if invalid.
 */
export function safeDateAgeMs(ts: any, nowMs: number = Date.now()): number | null {
  if (ts == null) return null;

  let tMs: number | null = null;

  if (typeof ts === "number") {
    tMs = ts < 1e12 ? ts * 1000 : ts; // seconds vs ms
  } else if (typeof ts === "string") {
    const n = Number(ts);
    if (Number.isFinite(n)) tMs = n < 1e12 ? n * 1000 : n;
    else {
      const d = new Date(ts);
      if (!Number.isNaN(d.getTime())) tMs = d.getTime();
    }
  } else if (ts instanceof Date) {
    tMs = ts.getTime();
  }

  if (tMs == null || !Number.isFinite(tMs)) return null;
  const age = nowMs - tMs;
  return Number.isFinite(age) ? Math.max(0, age) : null;
}

/* ---------------- Base URL helpers (fixes “relative /api hits FE origin”) ---------------- */

const RAW_BASE = (process.env.NEXT_PUBLIC_AION_API_BASE || "").trim().replace(/\/+$/, "");

/** Use for HTTP fetches. If env is unset, keeps same-origin relative paths working. */
export function apiUrl(path: string) {
  return RAW_BASE ? `${RAW_BASE}${path}` : path;
}

/** Convert the API base into ws/wss automatically. */
export function wsUrl(path: string) {
  if (!RAW_BASE) return path;
  const wsBase = RAW_BASE.startsWith("https://")
    ? RAW_BASE.replace("https://", "wss://")
    : RAW_BASE.replace("http://", "ws://");
  return `${wsBase}${path}`;
}

/* ---------------- Freshness helpers (NO_FEED / STALE / LIVE) ---------------- */

export type FeedStatus = "NO_FEED" | "STALE" | "LIVE";

/** Default staleness window used across AION panels. */
export const DEFAULT_STALE_MS = 5000;

/** Given an age_ms, classify feed status. */
export function feedStatus(ageMs: number | null | undefined, staleMs: number = DEFAULT_STALE_MS): FeedStatus {
  if (ageMs == null || !Number.isFinite(ageMs)) return "NO_FEED";
  return ageMs > staleMs ? "STALE" : "LIVE";
}

export function feedLabel(s: FeedStatus) {
  return s;
}

export function feedTone(s: FeedStatus): { bg: string; bd: string; fg: string } {
  if (s === "LIVE") return { bg: "bg-emerald-50", bd: "border-emerald-200", fg: "text-emerald-700" };
  if (s === "STALE") return { bg: "bg-amber-50", bd: "border-amber-200", fg: "text-amber-700" };
  return { bg: "bg-slate-50", bd: "border-slate-200", fg: "text-slate-500" };
}

export function FeedPill(props: { status: FeedStatus; right?: React.ReactNode; title?: string }) {
  const t = feedTone(props.status);
  return (
    <div
      title={props.title || ""}
      className={classNames(
        "inline-flex items-center gap-2 rounded-full border px-3 py-1 text-[10px] font-bold tracking-widest uppercase",
        t.bg,
        t.bd,
        t.fg
      )}
    >
      <span>{feedLabel(props.status)}</span>
      {props.right ? <span className="opacity-80">{props.right}</span> : null}
    </div>
  );
}

/* ---------------- Light-mode UI atoms ---------------- */

export function Card(props: { title: string; subtitle?: string; right?: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <div className="text-base font-bold tracking-tight text-slate-900 uppercase">{props.title}</div>
          {props.subtitle ? (
            <div className="mt-1 font-mono text-[11px] font-medium tracking-wide text-slate-500 uppercase">
              {props.subtitle}
            </div>
          ) : null}
        </div>

        {props.right ? <div className="shrink-0">{props.right}</div> : null}
      </div>

      {props.children}
    </div>
  );
}

export function StatRow(props: { label: string; value: React.ReactNode; hint?: string }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-slate-100 py-3 last:border-0">
      <div className="flex flex-col">
        <span className="text-xs font-semibold tracking-wide text-slate-700 uppercase">{props.label}</span>
        {props.hint ? <span className="text-[10px] leading-tight text-slate-500 italic">{props.hint}</span> : null}
      </div>

      <div className="font-mono text-sm font-bold tabular-nums text-slate-900">{props.value}</div>
    </div>
  );
}

export function MiniBar(props: { value: number; goodMin?: number; warnMin?: number; label?: string }) {
  const v = clamp01(props.value);
  const goodMin = props.goodMin ?? 0.975;
  const warnMin = props.warnMin ?? 0.85;

  const tone = v >= goodMin ? "bg-emerald-500" : v >= warnMin ? "bg-amber-500" : "bg-rose-500";

  return (
    <div className="w-full space-y-2">
      {props.label ? (
        <div className="text-[10px] font-bold tracking-widest text-slate-500 uppercase">{props.label}</div>
      ) : null}

      <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
        <div className={classNames("h-full transition-all duration-500 ease-out", tone)} style={{ width: `${Math.round(v * 100)}%` }} />
      </div>

      <div className="flex justify-between font-mono text-[9px] font-medium text-slate-500">
        <span>0.00</span>
        <span className="text-slate-900">{v.toFixed(3)}</span>
        <span>1.00</span>
      </div>
    </div>
  );
}

export function Button(
  props: React.ButtonHTMLAttributes<HTMLButtonElement> & { tone?: "primary" | "neutral" | "danger" }
) {
  const tone = props.tone || "neutral";

  const base =
    "inline-flex items-center justify-center rounded-lg px-4 py-2 text-[11px] font-bold tracking-widest uppercase transition active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed";

  const variants = {
    primary: "bg-[#1B74E4] text-white hover:bg-[#1B74E4]/90 shadow-sm",
    neutral: "bg-white text-slate-700 hover:bg-slate-50 border border-slate-200",
    danger: "bg-rose-600 text-white hover:bg-rose-700 shadow-sm",
  };

  return <button {...props} className={classNames(base, variants[tone], props.className)} />;
}

/* ---------------- DARK “data surface” atoms (fix unreadable panels) ---------------- */

export function DarkCard(props: {
  title: string;
  subtitle?: string;
  right?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-slate-700/30 bg-gradient-to-b from-[#0B1220] to-[#0A1020] p-6 shadow-[0_10px_30px_rgba(2,6,23,0.25)]">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <div className="text-base font-bold tracking-tight text-slate-100 uppercase">{props.title}</div>
          {props.subtitle ? (
            <div className="mt-1 font-mono text-[11px] font-medium tracking-wide text-slate-400 uppercase">
              {props.subtitle}
            </div>
          ) : null}
        </div>

        {props.right ? <div className="shrink-0">{props.right}</div> : null}
      </div>

      {props.children}
    </div>
  );
}

export function DarkStatRow(props: { label: string; value: React.ReactNode; hint?: string }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-slate-700/20 py-3 last:border-0">
      <div className="flex flex-col">
        <span className="text-xs font-semibold tracking-wide text-slate-300 uppercase">{props.label}</span>
        {props.hint ? <span className="text-[10px] leading-tight text-slate-400 italic">{props.hint}</span> : null}
      </div>

      <div className="font-mono text-sm font-bold tabular-nums text-slate-100">{props.value}</div>
    </div>
  );
}

/**
 * Dark mini bar (same semantics as MiniBar) for monitors placed on dark panels.
 * IMPORTANT: callers should pass 0..1 ONLY when feed is LIVE; otherwise show placeholder.
 */
export function DarkMiniBar(props: { value: number; goodMin?: number; warnMin?: number; label?: string }) {
  const v = clamp01(props.value);
  const goodMin = props.goodMin ?? 0.975;
  const warnMin = props.warnMin ?? 0.85;

  const tone = v >= goodMin ? "bg-emerald-400" : v >= warnMin ? "bg-amber-400" : "bg-rose-400";

  return (
    <div className="w-full space-y-2">
      {props.label ? (
        <div className="text-[10px] font-bold tracking-widest text-slate-400 uppercase">{props.label}</div>
      ) : null}

      <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-700/40">
        <div className={classNames("h-full transition-all duration-500 ease-out", tone)} style={{ width: `${Math.round(v * 100)}%` }} />
      </div>

      <div className="flex justify-between font-mono text-[9px] font-medium text-slate-500">
        <span>0.00</span>
        <span className="text-slate-200">{v.toFixed(3)}</span>
        <span>1.00</span>
      </div>
    </div>
  );
}