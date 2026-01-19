"use client";

import React from "react";

// --- Branding Constants from Tessaris Style Playbook ---
const TESSARIS_COLORS = {
  blue: "#1B74E4",    // tessarisBlue
  ink: "#0F172A",     // tessarisInk
  slate: "#64748B",   // tessarisGray
  emerald: "#10B981", // tessarisGreen
  amber: "#F59E0B",   // tessarisAmber
  rose: "#EF4444",    // tessarisRed
};

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

// --- Branding UI atoms ---

/**
 * Card: Updated to tessarisInk with subtle slate borders
 */
export function Card(props: { title: string; subtitle?: string; right?: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-[#0F172A] p-6 shadow-xl ring-1 ring-white/5">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <div className="text-lg font-bold tracking-tight text-white uppercase sm:text-base">
            {props.title}
          </div>
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

/**
 * StatRow: Optimized for technical resonance telemetry
 */
export function StatRow(props: { label: string; value: React.ReactNode; hint?: string }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-white/5 py-3 last:border-0">
      <div className="flex flex-col">
        <span className="text-xs font-semibold tracking-wide text-slate-300 uppercase">
          {props.label}
        </span>
        {props.hint ? (
          <span className="text-[10px] leading-tight text-slate-500 italic">
            {props.hint}
          </span>
        ) : null}
      </div>
      <div className="font-mono text-sm font-bold tabular-nums text-white">
        {props.value}
      </div>
    </div>
  );
}

/**
 * MiniBar: Updated with Tessaris brand color logic
 */
export function MiniBar(props: { value: number; goodMin?: number; warnMin?: number; label?: string }) {
  const v = clamp01(props.value);
  const goodMin = props.goodMin ?? 0.975; // Phase 6D Homeostasis Lock Threshold
  const warnMin = props.warnMin ?? 0.85;
  
  const tone = v >= goodMin 
    ? "bg-[#10B981] shadow-[0_0_8px_#10b98166]" 
    : v >= warnMin 
      ? "bg-[#F59E0B]" 
      : "bg-[#EF4444]";

  return (
    <div className="w-full space-y-2">
      {props.label ? (
        <div className="text-[10px] font-bold tracking-widest text-slate-400 uppercase">
          {props.label}
        </div>
      ) : null}
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
        <div 
          className={classNames("h-full transition-all duration-500 ease-out", tone)} 
          style={{ width: `${Math.round(v * 100)}%` }} 
        />
      </div>
      <div className="flex justify-between font-mono text-[9px] font-medium text-slate-500">
        <span>0.00</span>
        <span className="text-white">{v.toFixed(3)}</span>
        <span>1.00</span>
      </div>
    </div>
  );
}

/**
 * Button: Styled with Tessaris primary blue and ink-neutral tones
 */
export function Button(props: React.ButtonHTMLAttributes<HTMLButtonElement> & { tone?: "primary" | "neutral" | "danger" }) {
  const tone = props.tone || "neutral";
  
  const baseStyles = "inline-flex items-center justify-center rounded-lg px-4 py-2 text-[11px] font-bold tracking-widest uppercase transition-all active:scale-95 disabled:opacity-30 disabled:cursor-not-allowed";
  
  const variants = {
    primary: "bg-[#1B74E4] text-white hover:bg-[#1B74E4]/90 shadow-lg shadow-blue-900/20",
    neutral: "bg-slate-800 text-slate-200 hover:bg-slate-700 hover:text-white border border-slate-700",
    danger: "bg-rose-500/10 text-rose-400 border border-rose-500/20 hover:bg-rose-500 hover:text-white",
  };

  return (
    <button
      {...props}
      className={classNames(baseStyles, variants[tone], props.className)}
    />
  );
}