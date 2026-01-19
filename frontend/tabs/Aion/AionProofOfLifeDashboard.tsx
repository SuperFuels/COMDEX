// frontend/tabs/Aion/AionProofOfLifeDashboard.tsx
"use client";

import React, { useEffect, useState } from "react";

import { demo01Meta, Demo01MetabolismPanel } from "./demos/demo01_metabolism";
import { demo02Meta, Demo02AdrPanel } from "./demos/demo02_immune_adr";
import { demo03Meta, Demo03HeartbeatPanel } from "./demos/Demo03Heartbeat";

/* ---------------- Types only (keep local, minimal) ---------------- */

type PhiState = any;
type AdrBundle = any;
type HeartbeatEnvelope = any;

/* ---------------- API helpers ---------------- */

function apiBase(): string | null {
  const raw = (process.env.NEXT_PUBLIC_API_URL || "").trim();
  if (!raw) return null;
  return raw.replace(/\/+$/, "");
}

function apiUrl(path: string): string {
  const base = apiBase();
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  if (!base) return `/api${cleanPath}`;
  const normalized = base.replace(/\/api$/i, "");
  return `${normalized}/api${cleanPath}`;
}

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${url} -> ${res.status} ${res.statusText}${text ? `: ${text}` : ""}`);
  }
  return (await res.json()) as T;
}

async function post(path: string): Promise<void> {
  await fetchJson<any>(apiUrl(path), { method: "POST" });
}

/* ---------------- Small UI helpers ---------------- */

function classNames(...xs: Array<string | false | null | undefined>) {
  return xs.filter(Boolean).join(" ");
}

function PillarSection(props: {
  id: string;
  container: React.ReactNode;
  title: string;
  pillar: string;
  testName: string;
  copy: string;
}) {
  return (
    <section id={props.id} className="grid grid-cols-1 gap-6 lg:grid-cols-5">
      <div className="lg:col-span-3">{props.container}</div>
      <div className="lg:col-span-2">
        <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
          <div className="text-xs font-medium uppercase tracking-wider text-white/60">{props.pillar}</div>
          <div className="mt-2 text-lg font-semibold text-white">{props.title}</div>
          <div className="mt-1 text-sm text-white/75">
            UI Test Name: <span className="font-medium text-white">{props.testName}</span>
          </div>
          <p className="mt-4 text-sm leading-6 text-white/80">{props.copy}</p>
        </div>
      </div>
    </section>
  );
}

/* ---------------- Data hook (polls all demos) ---------------- */

function useAionDemoData(pollMs = 500) {
  const [phi, setPhi] = useState<PhiState | null>(null);
  const [adr, setAdr] = useState<AdrBundle | null>(null);
  const [heartbeat, setHeartbeat] = useState<HeartbeatEnvelope | null>(null);

  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    let t: any = null;

    const tick = async () => {
      try {
        const [phiRes, adrRes, hbRes] = await Promise.allSettled([
          fetchJson<PhiState>(apiUrl("/phi")),
          fetchJson<AdrBundle>(apiUrl("/adr")),
          fetchJson<HeartbeatEnvelope>(apiUrl("/heartbeat?namespace=demo")),
        ]);

        if (cancelled) return;

        if (phiRes.status === "fulfilled") setPhi(phiRes.value);
        if (adrRes.status === "fulfilled") setAdr(adrRes.value);
        if (hbRes.status === "fulfilled") setHeartbeat(hbRes.value);

        const errors: string[] = [];
        if (phiRes.status === "rejected") errors.push(phiRes.reason?.message || String(phiRes.reason));
        if (adrRes.status === "rejected") errors.push(adrRes.reason?.message || String(adrRes.reason));
        if (hbRes.status === "rejected") errors.push(hbRes.reason?.message || String(hbRes.reason));
        setErr(errors.length ? errors.join(" • ") : null);
      } catch (e: any) {
        if (!cancelled) setErr(e?.message || String(e));
      } finally {
        if (!cancelled) setLoading(false);
        t = setTimeout(tick, pollMs);
      }
    };

    tick();
    return () => {
      cancelled = true;
      if (t) clearTimeout(t);
    };
  }, [pollMs]);

  return { phi, adr, heartbeat, err, loading };
}

/* ---------------- Page ---------------- */

export default function AionProofOfLifeDashboard() {
  const { phi, adr, heartbeat, err, loading } = useAionDemoData(500);

  // shared busy flag: demo panels only read this to disable buttons + show labels
  const [actionBusy, setActionBusy] = useState<string | null>(null);

  async function runBusy(name: string, fn: () => Promise<void>) {
    try {
      setActionBusy(name);
      await fn();
    } finally {
      setActionBusy(null);
    }
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-white">
      <div className="mx-auto max-w-6xl px-5 py-10">
        <header className="mb-8">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <div className="text-xs font-medium uppercase tracking-wider text-white/60">AION • Proof of Life</div>
              <h1 className="mt-2 text-2xl font-semibold tracking-tight">Act 1 — Synthetic Homeostasis</h1>
              <p className="mt-2 max-w-2xl text-sm text-white/70">
                Metabolism (Φ), Immune Response (ADR), and Heartbeat (Θ) are live. Everything else stays modular and drops in as a new demo panel.
              </p>
            </div>

            <div
              className={classNames(
                "rounded-full px-3 py-1 text-xs",
                err ? "bg-rose-500/20 text-rose-200" : "bg-emerald-500/15 text-emerald-200"
              )}
            >
              {loading ? "Connecting…" : err ? "Bridge offline / partial" : "Live"}
            </div>
          </div>

          {err ? <div className="mt-3 text-xs text-white/50">{err}</div> : null}
        </header>

        {/* Demo 01 */}
        <PillarSection
          id={demo01Meta.id}
          pillar={demo01Meta.pillar}
          title={demo01Meta.title}
          testName={demo01Meta.testName}
          copy={demo01Meta.copy}
          container={
            <Demo01MetabolismPanel
              phi={phi}
              actionBusy={actionBusy}
              onReset={() => runBusy("reset", () => post("/demo/phi/reset"))}
              onInjectEntropy={() => runBusy("inject", () => post("/demo/phi/inject_entropy"))}
              onRecover={() => runBusy("recover", () => post("/demo/phi/recover"))}
            />
          }
        />

        <div className="my-10 h-px w-full bg-white/10" />

        {/* Demo 02 */}
        <PillarSection
          id={demo02Meta.id}
          pillar={demo02Meta.pillar}
          title={demo02Meta.title}
          testName={demo02Meta.testName}
          copy={demo02Meta.copy}
          container={
            <Demo02AdrPanel
              adr={adr}
              actionBusy={actionBusy}
              onInject={() => runBusy("adr_inject", () => post("/demo/adr/inject"))}
              onRun={() => runBusy("adr_run", () => post("/demo/adr/run"))}
            />
          }
        />

        <div className="my-10 h-px w-full bg-white/10" />

        {/* Demo 03 */}
        <PillarSection
          id={demo03Meta.id}
          pillar={demo03Meta.pillar}
          title={demo03Meta.title}
          testName={demo03Meta.testName}
          copy={demo03Meta.copy}
          container={<Demo03HeartbeatPanel heartbeat={heartbeat} namespace="demo" />}
        />

        <footer className="mt-10 text-xs text-white/45">
          Tip: keep the page dumb. Each demo lives in <span className="font-mono">./demos/</span> and exports{" "}
          <span className="font-mono">meta + Panel</span>.
        </footer>
      </div>
    </div>
  );
}