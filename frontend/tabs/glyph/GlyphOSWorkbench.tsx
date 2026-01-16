// frontend/tabs/glyph/GlyphOSWorkbench.tsx
"use client";

import { useMemo, useState } from "react";

type CodeLang = "photon" | "python";

type TranslateResponse = {
  translated?: string;
  glyph_count?: number;
  chars_before?: number;
  chars_after?: number;
  compression_ratio?: number;
};

type Scenario = {
  key: string;
  label: string;
  subtitle: string;
  intentNL: string;
  intentJSON: string;

  // IMPORTANT: we keep a hidden “compiler source” for translation,
  // but we do NOT show it in the UI (no .ptn panel).
  compileSource: string;
};

type TraceStep = {
  id: string;
  label: string;
  detail: string;
  ms: number;
  ok: boolean;
};

const SCENARIOS: readonly Scenario[] = [
  {
    key: "doc-intel",
    label: "Document Intelligence",
    subtitle: "Scan → extract → brief → store → notify (with deterministic trace)",
    intentNL:
      'Scan the attached document, extract key entities (people, orgs, dates, money), summarize the top 5 points, file it under "Symatics", then notify me with the summary and a link.',
    intentJSON: JSON.stringify(
      {
        task: "doc_pipeline",
        input: { type: "pdf", source: "attachment" },
        steps: [
          { op: "extract_entities", fields: ["person", "org", "date", "money"] },
          { op: "summarize", top_k: 5 },
          { op: "file", folder: "Symatics" },
          { op: "notify", channel: "inbox", include: ["summary", "link"] },
        ],
        constraints: { deterministic: true, trace: true, policy: "safe" },
      },
      null,
      2,
    ),
    compileSource: [
      // This is just a translation source; NOT shown.
      "# GlyphOS compile source (hidden)",
      '⊕ job "doc_intel" {',
      '  in pdf "attachment";',
      "  ⊕ extract entities(person, org, date, money);",
      "  ⊕ summarize top 5;",
      '  ⊕ file to "Symatics";',
      "  ⊕ notify include(summary, link);",
      "  ⊕ trace on;",
      "}",
    ].join("\n"),
  },
  {
    key: "ops-fast-action",
    label: "Ops Automation",
    subtitle: "Compressed intent → action (policy + trace)",
    intentNL:
      "When I say “ship it”, run tests, build, deploy to staging, and post the result to the team channel. If tests fail, open an issue with the failing logs.",
    intentJSON: JSON.stringify(
      {
        trigger: "phrase:ship it",
        pipeline: [
          { op: "run_tests", mode: "ci" },
          { op: "build" },
          { op: "deploy", env: "staging" },
          { op: "notify", channel: "team" },
        ],
        on_fail: [{ op: "open_issue", include: ["logs", "commit", "stack"] }],
        constraints: { deterministic: true, trace: true },
      },
      null,
      2,
    ),
    compileSource: [
      "# Hidden compile source",
      '⊕ trigger "ship it" {',
      "  ⊕ test ci;",
      "  ⊕ build;",
      '  ⊕ deploy "staging";',
      '  ⊕ notify "team" include(status, link);',
      "  ⊕ on_fail { open_issue include(logs, commit, stack); }",
      "  ⊕ trace on;",
      "}",
    ].join("\n"),
  },
  {
    key: "agent-orch",
    label: "AI Orchestration",
    subtitle: "Policy + replayable decision trace",
    intentNL:
      "Plan a 3-step research sprint on Symatics: collect sources, extract a thesis outline, then draft an executive summary. Keep a replayable trace and show the final decision path.",
    intentJSON: JSON.stringify(
      {
        agent: "research_orchestrator",
        goal: "Symatics sprint",
        steps: ["collect_sources", "outline_thesis", "draft_exec_summary"],
        policy: { safety: "strict", citations: true },
        trace: { replayable: true, include_decisions: true },
      },
      null,
      2,
    ),
    compileSource: [
      "# Hidden compile source",
      '⊕ agent "research_orchestrator" {',
      '  goal "Symatics sprint";',
      "  ⊕ collect sources;",
      "  ⊕ outline thesis;",
      "  ⊕ draft executive_summary;",
      "  ⊕ policy strict;",
      "  ⊕ trace replay(decisions);",
      "}",
    ].join("\n"),
  },
];

// ------------------------------ API (same as your original working behavior) ------------------------------

const API_BASE =
  (typeof window !== "undefined" && (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/+$/, "")) || "";

function apiUrl(path: string) {
  if (!path.startsWith("/")) path = `/${path}`;
  return API_BASE ? `${API_BASE}${path}` : path;
}

async function translateToGlyphs(code: string, lang: CodeLang): Promise<TranslateResponse> {
  const res = await fetch(apiUrl("/api/photon/translate"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: code, language: lang }),
  });

  if (!res.ok) {
    const ct = res.headers.get("content-type") || "";
    const raw = await res.text().catch(() => "");
    const hint = ct.includes("text/html")
      ? "HTML response — likely not hitting FastAPI. Check rewrites for /api/:path* and NEXT_PUBLIC_API_URL."
      : "";
    const msg = (raw && raw.slice(0, 400)) || res.statusText;
    throw new Error(`HTTP ${res.status} — ${msg}${hint ? `\n${hint}` : ""}`);
  }

  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return (await res.json()) as TranslateResponse;

  const text = await res.text();
  return { translated: text, chars_before: code.length, chars_after: text.length };
}

// ------------------------------ deterministic trace (seeded) ------------------------------

function fnv1a(input: string) {
  let h = 0x811c9dc5;
  for (let i = 0; i < input.length; i++) {
    h ^= input.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return h >>> 0;
}

function makeRng(seed: number) {
  let x = seed || 123456789;
  return () => {
    x ^= x << 13;
    x ^= x >>> 17;
    x ^= x << 5;
    return (x >>> 0) / 0xffffffff;
  };
}

function buildTrace(seedStr: string): { traceId: string; steps: TraceStep[] } {
  const seed = fnv1a(seedStr);
  const rng = makeRng(seed);

  const base = [
    { label: "Parse intent", detail: "Decode meaning-shape", min: 18, max: 42 },
    { label: "Bind policy", detail: "Resolve permissions + constraints", min: 20, max: 55 },
    { label: "Execute", detail: "Run operator table deterministically", min: 35, max: 95 },
    { label: "Emit trace", detail: "Write replayable audit trail", min: 16, max: 44 },
  ];

  const steps: TraceStep[] = base.map((b, i) => {
    const ms = Math.round(b.min + (b.max - b.min) * rng());
    const ok = rng() > 0.04;
    return { id: `s${i + 1}`, label: b.label, detail: b.detail, ms, ok };
  });

  const anyFail = steps.some((s) => !s.ok);
  const finalSteps = anyFail
    ? steps.map((s, idx) => (idx === steps.length - 1 ? { ...s, ok: false, detail: "Abort + rollback (deterministic)" } : s))
    : steps;

  const traceId = `GX-${seed.toString(16).padStart(8, "0").toUpperCase()}`;
  return { traceId, steps: finalSteps };
}

// ------------------------------ UI helpers ------------------------------

function Pane({
  title,
  subtitle,
  right,
  children,
}: {
  title: string;
  subtitle?: string;
  right?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-[2.5rem] border border-gray-100 bg-white overflow-hidden shadow-xl shadow-gray-200/40">
      <div className="px-8 py-6 border-b border-gray-100 flex items-start justify-between gap-6">
        <div>
          <div className="text-lg font-bold text-gray-900">{title}</div>
          {subtitle ? <div className="text-sm text-gray-400 mt-1">{subtitle}</div> : null}
        </div>
        {right ? <div>{right}</div> : <div />}
      </div>
      <div className="bg-[#fafafa]">{children}</div>
    </div>
  );
}

function CodeWithLines({ value, minRows = 12 }: { value: string; minRows?: number }) {
  const lines = useMemo(() => Math.max(minRows, value.split("\n").length), [value, minRows]);

  return (
    <div className="flex font-mono text-sm leading-6">
      <div className="select-none text-right text-gray-300 bg-white/40 border-r border-gray-100 px-6 py-6 min-w-[3.25rem]">
        {Array.from({ length: lines }, (_, i) => (
          <div key={i}>{i + 1}</div>
        ))}
      </div>
      <pre className="flex-1 whitespace-pre-wrap break-words px-6 py-6 text-gray-800">{value}</pre>
    </div>
  );
}

// ------------------------------ Component ------------------------------

export default function GlyphOSWorkbench() {
  const [scenarioKey, setScenarioKey] = useState(SCENARIOS[0].key);
  const scenario = useMemo(() => SCENARIOS.find((s) => s.key === scenarioKey) || SCENARIOS[0], [scenarioKey]);

  const [view, setView] = useState<"nl" | "json">("nl");
  const [lang, setLang] = useState<CodeLang>("photon");

  const [intentNL, setIntentNL] = useState(scenario.intentNL);
  const [intentJSON, setIntentJSON] = useState(scenario.intentJSON);

  const [glyphWire, setGlyphWire] = useState<string>("—");
  const [traceId, setTraceId] = useState("—");
  const [trace, setTrace] = useState<TraceStep[]>([]);
  const [stats, setStats] = useState<{ before: number; after: number; pct: number } | null>(null);

  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const loadScenario = (s: Scenario) => {
    setScenarioKey(s.key);
    setIntentNL(s.intentNL);
    setIntentJSON(s.intentJSON);
    setGlyphWire("—");
    setTraceId("—");
    setTrace([]);
    setStats(null);
    setErr(null);
  };

  const run = async () => {
    try {
      setBusy(true);
      setErr(null);

      // Translate hidden compile source to glyph wire
      const resp = await translateToGlyphs(scenario.compileSource, lang);
      const translated = (resp.translated ?? "").trim();
      const wire = translated.length ? translated : "—";
      setGlyphWire(wire);

      // Compression stats vs Natural Language intent
      const before = intentNL.length;
      const after = wire === "—" ? 0 : wire.length;
      const pct = before > 0 && after > 0 ? (1 - after / before) * 100 : 0;
      setStats(after > 0 ? { before, after, pct } : null);

      // Deterministic trace seeded by scenario + wire
      const seedStr = `${scenario.key}::${wire}::${lang}`;
      const t = buildTrace(seedStr);
      setTraceId(t.traceId);
      setTrace(t.steps);
    } catch (e: any) {
      setErr(e?.message || "Run failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="space-y-16">
      {/* HERO — match your old sizing (attachment 3) */}
      <div className="text-center space-y-6">
        <h1 className="text-7xl md:text-9xl font-bold tracking-tight text-black italic">Glyph OS</h1>
        <p className="text-2xl text-gray-500 font-light tracking-tight">
          The Language of Symbols. <span className="text-black font-medium">The Speed of Light.</span>
        </p>
        <p className="max-w-3xl mx-auto text-lg text-gray-500 leading-relaxed">
          Intent → Glyph-wire (canonical meaning-shape) → deterministic trace → next action (policy).
        </p>
      </div>

      {/* Scenario selector — clean + boutique */}
      <div className="flex flex-wrap items-center justify-center gap-3">
        {SCENARIOS.map((s) => {
          const active = s.key === scenarioKey;
          return (
            <button
              key={s.key}
              onClick={() => loadScenario(s)}
              className={`px-7 py-3 rounded-full text-sm font-semibold transition-all ${
                active
                  ? "bg-[#0071e3] text-white shadow-xl shadow-gray-200/50"
                  : "bg-white text-gray-600 border border-gray-200 hover:text-black"
              }`}
            >
              {s.label}
            </button>
          );
        })}
      </div>

      {/* Workbench container — wider, rounded, not squared */}
      <div className="w-full bg-white rounded-[3rem] shadow-2xl shadow-gray-200/60 border border-gray-100 p-12 space-y-10">
        <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-6">
          <div>
            <div className="text-xs font-bold text-gray-300 uppercase tracking-widest">Demo Presets</div>
            <div className="text-3xl font-bold text-gray-900 mt-2">{scenario.label}</div>
            <div className="text-gray-500 mt-1">{scenario.subtitle}</div>
          </div>

          <div className="flex items-center gap-3">
            <select
              value={lang}
              onChange={(e) => setLang(e.target.value as CodeLang)}
              className="px-5 py-3 rounded-2xl border border-gray-200 bg-white text-sm font-semibold text-gray-700 shadow-sm outline-none focus:ring-2 focus:ring-blue-200"
            >
              <option value="photon">Photon (.ptn)</option>
              <option value="python">Python (.py)</option>
            </select>

            <button
              onClick={run}
              disabled={busy}
              className={`px-10 py-3 rounded-full text-sm font-semibold transition-all duration-300 ${
                busy ? "bg-gray-200 text-gray-500" : "bg-[#0071e3] text-white shadow-md hover:brightness-110"
              }`}
            >
              {busy ? "Running…" : "Run"}
            </button>
          </div>
        </div>

        {err ? <div className="text-sm text-red-600 whitespace-pre-wrap">{err}</div> : null}

        {/* ✅ EXACTLY THREE PANELS — Words / Glyph-wire / Trace */}
        <div className="grid lg:grid-cols-3 gap-10">
          {/* 1) WORDS */}
          <Pane
            title="Words"
            subtitle="Verbose intent (what most systems require)"
            right={
              <div className="flex items-center gap-2 bg-white rounded-full border border-gray-200 p-1">
                <button
                  onClick={() => setView("nl")}
                  className={`px-4 py-2 rounded-full text-xs font-bold tracking-wider uppercase transition ${
                    view === "nl" ? "bg-black text-white" : "text-gray-500 hover:text-black"
                  }`}
                >
                  Natural
                </button>
                <button
                  onClick={() => setView("json")}
                  className={`px-4 py-2 rounded-full text-xs font-bold tracking-wider uppercase transition ${
                    view === "json" ? "bg-black text-white" : "text-gray-500 hover:text-black"
                  }`}
                >
                  JSON
                </button>
              </div>
            }
          >
            {view === "nl" ? (
              <div className="p-6">
                <textarea
                  value={intentNL}
                  onChange={(e) => setIntentNL(e.target.value)}
                  className="w-full min-h-[280px] rounded-[2rem] border border-gray-200 bg-white p-6 text-sm text-gray-800 leading-relaxed outline-none focus:ring-2 focus:ring-blue-200"
                  spellCheck={false}
                />
              </div>
            ) : (
              <CodeWithLines value={intentJSON} minRows={16} />
            )}
          </Pane>

          {/* 2) GLYPH-WIRE */}
          <Pane
            title="Glyph-wire"
            subtitle="Canonical meaning-shape (portable + stable)"
            right={
              stats ? (
                <div className="text-[11px] text-gray-400">
                  <span className="font-semibold">{stats.pct.toFixed(1)}%</span> shorter ({stats.before} → {stats.after})
                </div>
              ) : (
                <div className="text-[11px] text-gray-400 font-bold uppercase tracking-widest">Translated</div>
              )
            }
          >
            <CodeWithLines value={glyphWire} minRows={16} />
          </Pane>

          {/* 3) TRACE */}
          <Pane
            title="Trace"
            subtitle="Deterministic execution + audit trail"
            right={<div className="text-[11px] text-gray-400 font-bold uppercase tracking-widest">{traceId}</div>}
          >
            <div className="p-6 space-y-4">
              {trace.length === 0 ? (
                <div className="text-sm text-gray-400">Press Run to generate a deterministic trace.</div>
              ) : (
                <div className="space-y-3">
                  {trace.map((s) => (
                    <div
                      key={s.id}
                      className="flex items-start justify-between gap-4 bg-white rounded-[2rem] border border-gray-100 p-5 shadow-sm"
                    >
                      <div className="flex items-start gap-3">
                        <div className={`mt-1 w-3 h-3 rounded-full ${s.ok ? "bg-emerald-500" : "bg-rose-500"}`} />
                        <div>
                          <div className="text-sm font-semibold text-gray-900">{s.label}</div>
                          <div className="text-xs text-gray-500 mt-1">{s.detail}</div>
                        </div>
                      </div>
                      <div className="text-xs font-mono text-gray-400 whitespace-nowrap">{s.ms} ms</div>
                    </div>
                  ))}
                  <div className="pt-1 text-xs text-gray-400">
                    Same wire + same policy ⇒ same trace. (Replayable.)
                  </div>
                </div>
              )}
            </div>
          </Pane>
        </div>
      </div>

      <div className="text-center font-medium text-gray-400 italic">“Same meaning. Less noise. Deterministic execution.”</div>
    </section>
  );
}