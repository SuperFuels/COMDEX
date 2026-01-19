"use client";

import React from "react";

export function classNames(...xs: Array<string | false | null | undefined>) {
  return xs.filter(Boolean).join(" ");
}

export function clamp01(x: number) {
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

export function safeDateAgeMs(iso?: string | null): number | null {
  if (!iso) return null;
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return null;
  return Date.now() - t;
}

// --- Branding UI atoms ---
export function Card(props: { title: string; subtitle?: string; right?: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-5 shadow-sm">
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <div className="text-base font-semibold tracking-tight text-white">{props.title}</div>
          {props.subtitle ? <div className="mt-1 text-sm text-white/70">{props.subtitle}</div> : null}
        </div>
        {props.right ? <div className="shrink-0">{props.right}</div> : null}
      </div>
      {props.children}
    </div>
  );
}

export function StatRow(props: { label: string; value: React.ReactNode; hint?: string }) {
  return (
    <div className="flex items-center justify-between gap-3 py-2">
      <div>
        <div className="text-sm text-white/80">{props.label}</div>
        {props.hint ? <div className="text-xs text-white/50">{props.hint}</div> : null}
      </div>
      <div className="text-sm font-semibold tabular-nums text-white">{props.value}</div>
    </div>
  );
}

export function MiniBar(props: { value: number; goodMin?: number; warnMin?: number; label?: string }) {
  const v = clamp01(props.value);
  const goodMin = props.goodMin ?? 0.95;
  const warnMin = props.warnMin ?? 0.6;
  const tone = v >= goodMin ? "bg-emerald-400" : v >= warnMin ? "bg-amber-300" : "bg-rose-400";

  return (
    <div className="w-full">
      {props.label ? <div className="mb-1 text-xs text-white/60">{props.label}</div> : null}
      <div className="h-3 w-full rounded-full bg-white/10">
        <div className={classNames("h-3 rounded-full", tone)} style={{ width: `${Math.round(v * 100)}%` }} />
      </div>
      <div className="mt-1 flex justify-between text-[11px] text-white/50">
        <span>0.00</span>
        <span className="tabular-nums">{v.toFixed(2)}</span>
        <span>1.00</span>
      </div>
    </div>
  );
}

export function Button(props: React.ButtonHTMLAttributes<HTMLButtonElement> & { tone?: "primary" | "neutral" | "danger" }) {
  const tone = props.tone || "neutral";
  const cls =
    tone === "primary"
      ? "bg-white text-black hover:bg-white/90"
      : tone === "danger"
      ? "bg-rose-500 text-white hover:bg-rose-500/90"
      : "bg-white/10 text-white hover:bg-white/15";

  return (
    <button
      {...props}
      className={classNames(
        "inline-flex items-center justify-center rounded-xl px-3 py-2 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-60",
        cls,
        props.className
      )}
    />
  );
}