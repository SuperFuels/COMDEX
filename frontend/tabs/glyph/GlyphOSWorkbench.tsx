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
  intentNL: string;
  intentJSON: string;
  glyphProgram: string; // .ptn-ish source
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
    glyphProgram: [
      "# GlyphOS program (Photon/.ptn style)",
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
    label: "Compressed Intent → Action",
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
    glyphProgram: [
      "# “Meaning in motion”",
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
    label: "AI Orchestration (Policy + Trace)",
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
    glyphProgram: [
      "# AI orchestration with deterministic trace",
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

// ------------------------------ API (same behavior as your original) ------------------------------

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

// ------------------------------ tiny deterministic hash + rng ------------------------------

function fnv1a(input: string) {
  let h = 0x811c9dc5;
  for (let i = 0; i < input.length; i++) {
    h ^= input.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  // unsigned
  return h >>> 0;
}

function makeRng(seed: number) {
  // xorshift32
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
    { label: "Parse intent", detail: "Decode glyph-wire program", min: 18, max: 42 },
    { label: "Bind resources", detail: "Resolve inputs / permissions / policy", min: 20, max: 55 },
    { label: "Execute operators", detail: "Run operator table deterministically", min: 35, max: 90 },
    { label: "Emit trace", detail: "Write replayable audit + decision path", min: 16, max: 44 },
  ];

  const steps: TraceStep[] = base.map((b, i) => {
    const ms = Math.round(b.min + (b.max - b.min) * rng());
    const ok = rng() > 0.04; // small chance of fail for realism (still deterministic)
    return {
      id: `s${i + 1}`,
      label: b.label,
      detail: b.detail,
      ms,
      ok,
    };
  });

  // If any fail, mark last as fail-cascade for “deterministic abort”
  const anyFail = steps.some((s) => !s.ok);
  const finalSteps = anyFail
    ? steps.map((s, idx) =>
        idx === steps.length - 1 ? { ...s, ok: false, detail: "Abort + rollback (deterministic)" } : s,
      )
    : steps;

  const traceId = `GX-${seed.toString(16).padStart(8, "0").toUpperCase()}`;
  return { traceId, steps: finalSteps };
}

// ------------------------------ UI ------------------------------

function Pill({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center px-3 py-1 rounded-full text-[11px] font-bold tracking-wider uppercase bg-blue-50 text-[#0071e3] border border-blue-100">
      {children}
    </span>
  );
}

function Pane({
  title,
  right,
  children,
}: {
  title: string;
  right?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-[2rem] border border-gray-100 bg-white overflow-hidden shadow-sm">
      <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between gap-4">
        <div className="text-sm font-bold text-gray-700">{title}</div>
        {right ? <div>{right}</div> : <div />}
      </div>
      <div className="bg-[#fafafa]">{children}</div>
    </div>
  );
}

function TextAreaWithLines({
  value,
  onChange,
  readOnly,
  minRows = 10,
}: {
  value: string;
  onChange?: (v: string) => void;
  readOnly?: boolean;
  minRows?: number;
}) {
  const lines = useMemo(() => Math.max(1, value.split("\n").length), [value]);

  return (
    <div className="flex font-mono text-sm leading-6">
      <div className="select-none text-right text-gray-300 bg-white/40 border-r border-gray-100 px-4 py-4 min-w-[3rem]">
        {Array.from({ length: Math.max(minRows, lines) }, (_, i) => (
          <div key={i}>{i + 1}</div>
        ))}
      </div>

      {readOnly ? (
        <pre className="flex-1 whitespace-pre-wrap break-words px-4 py-4 text-gray-800">
          {value && value.trim().length ? value : "—"}
        </pre>
      ) : (
        <textarea
          value={value}
          onChange={(e) => onChange?.(e.target.value)}
          rows={Math.max(minRows, lines)}
          spellCheck={false}
          className="flex-1 resize-none bg-transparent px-4 py-4 outline-none text-gray-800"
        />
      )}
    </div>
  );
}

export default function GlyphOSWorkbench() {
  const [scenarioKey, setScenarioKey] = useState<string>(SCENARIOS[0].key);
  const scenario = useMemo(() => SCENARIOS.find((s) => s.key === scenarioKey) || SCENARIOS[0], [scenarioKey]);

  const [view, setView] = useState<"nl" | "json">("nl");
  const [lang, setLang] = useState<CodeLang>("photon");

  const [intentNL, setIntentNL] = useState(scenario.intentNL);
  const [intentJSON, setIntentJSON] = useState(scenario.intentJSON);
  const [program, setProgram] = useState(scenario.glyphProgram);

  const [glyphWire, setGlyphWire] = useState<string>("—");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const [traceId, setTraceId] = useState<string>("—");
  const [trace, setTrace] = useState<TraceStep[]>([]);

  const [stats, setStats] = useState<{ before: number; after: number; pct: number } | null>(null);

  // Update editors when scenario changes (but preserve if user started editing heavily)
  const loadScenario = (s: Scenario) => {
    setScenarioKey(s.key);
    setIntentNL(s.intentNL);
    setIntentJSON(s.intentJSON);
    setProgram(s.glyphProgram);
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

      // 1) compile/translate program → glyph wire
      const resp = await translateToGlyphs(program, lang);
      const translated = resp.translated ?? "";
      const wire = translated && translated.trim().length ? translated : "—";
      setGlyphWire(wire);

      // show “meaning compression” against NL (what user *wants*)
      const before = intentNL.length;
      const after = wire === "—" ? 0 : wire.length;
      const pct = before > 0 && after > 0 ? (1 - after / before) * 100 : 0;
      setStats(after > 0 ? { before, after, pct } : null);

      // 2) deterministic trace (seeded by scenario + wire)
      const seedStr = `${scenarioKey}::${wire}::${lang}`;
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
      {/* Hero (keep your original vibe) */}
      <div className="text-center space-y-6">
        <h1 className="text-7xl md:text-9xl font-bold tracking-tight text-black italic">Glyph OS</h1>
        <p className="text-2xl text-gray-500 font-light tracking-tight">
          The Language of Symbols. <span className="text-black font-medium">The Speed of Light.</span>
        </p>
        <p className="max-w-2xl mx-auto text-lg text-gray-500 leading-relaxed">
          Compressed intent → deterministic execution → replayable trace. Built for AI orchestration and meaning-native computation.
        </p>
      </div>

      {/* Scenario selector (boutique, not cluttered) */}
      <div className="flex flex-wrap items-center justify-center gap-3">
        {SCENARIOS.map((s) => {
          const active = s.key === scenarioKey;
          return (
            <button
              key={s.key}
              onClick={() => loadScenario(s)}
              className={`px-6 py-3 rounded-full text-sm font-semibold transition-all ${
                active ? "bg-black text-white shadow-md" : "bg-white text-gray-600 border border-gray-200 hover:text-black"
              }`}
            >
              {s.label}
            </button>
          );
        })}
      </div>

      {/* Main Workbench */}
      <div className="w-full bg-white rounded-[2.5rem] shadow-xl shadow-gray-200/50 border border-gray-100 p-10 space-y-10">
        <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-6">
          <div className="space-y-2">
            <div className="text-xs font-bold text-gray-300 uppercase tracking-widest">Meaning → Wire → Execution</div>
            <div className="text-sm text-gray-500">
              Compare verbose intent with a compact glyph program, then run a deterministic trace.
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="hidden md:flex items-center gap-2">
              <Pill>Deterministic</Pill>
              <Pill>Replayable Trace</Pill>
            </div>

            <select
              value={lang}
              onChange={(e) => setLang(e.target.value as CodeLang)}
              className="px-4 py-3 rounded-2xl border border-gray-200 bg-white text-sm font-semibold text-gray-700 shadow-sm outline-none focus:ring-2 focus:ring-blue-200"
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

        {/* Editors */}
        <div className="grid md:grid-cols-2 gap-8">
          <Pane
            title="VERBOSE INTENT"
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
                  className="w-full min-h-[220px] rounded-2xl border border-gray-200 bg-white p-5 text-sm text-gray-800 leading-relaxed outline-none focus:ring-2 focus:ring-blue-200"
                  spellCheck={false}
                />
              </div>
            ) : (
              <TextAreaWithLines value={intentJSON} onChange={setIntentJSON} minRows={12} />
            )}
          </Pane>

          <Pane
            title="GLYPH PROGRAM (.PTN)"
            right={<div className="text-[11px] text-gray-400 font-bold uppercase tracking-widest">Meaning-native</div>}
          >
            <TextAreaWithLines value={program} onChange={setProgram} minRows={12} />
          </Pane>
        </div>

        {/* Output + Trace */}
        <div className="grid md:grid-cols-2 gap-8">
          <Pane
            title="GLYPH WIRE (COMPACT)"
            right={
              stats ? (
                <div className="text-[11px] text-gray-400">
                  <span className="font-semibold">{stats.pct.toFixed(1)}%</span> shorter (NL {stats.before} → wire{" "}
                  {stats.after})
                </div>
              ) : (
                <div className="text-[11px] text-gray-400 font-bold uppercase tracking-widest">Translated</div>
              )
            }
          >
            <TextAreaWithLines value={glyphWire} readOnly minRows={12} />
          </Pane>

          <Pane
            title="DETERMINISTIC TRACE"
            right={<div className="text-[11px] text-gray-400 font-bold uppercase tracking-widest">Trace ID: {traceId}</div>}
          >
            <div className="p-6 space-y-4">
              {trace.length === 0 ? (
                <div className="text-sm text-gray-400">Run to generate a replayable execution trace.</div>
              ) : (
                <div className="space-y-3">
                  {trace.map((s) => (
                    <div
                      key={s.id}
                      className="flex items-start justify-between gap-4 bg-white rounded-2xl border border-gray-100 p-4 shadow-sm"
                    >
                      <div className="flex items-start gap-3">
                        <div
                          className={`mt-0.5 w-3 h-3 rounded-full ${
                            s.ok ? "bg-emerald-500" : "bg-rose-500"
                          }`}
                        />
                        <div>
                          <div className="text-sm font-semibold text-gray-800">{s.label}</div>
                          <div className="text-xs text-gray-500 mt-0.5">{s.detail}</div>
                        </div>
                      </div>
                      <div className="text-xs font-mono text-gray-400">{s.ms}ms</div>
                    </div>
                  ))}

                  <div className="pt-2 text-xs text-gray-400">
                    Same wire + same policy ⇒ same trace. (This is the “OS” part.)
                  </div>
                </div>
              )}
            </div>
          </Pane>
        </div>
      </div>

      <div className="text-center font-medium text-gray-400 italic">“Same meaning. Less noise. Faster execution.”</div>
    </section>
  );
}