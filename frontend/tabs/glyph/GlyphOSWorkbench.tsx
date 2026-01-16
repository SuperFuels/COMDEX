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

type PolicyKey = "deterministic" | "conservative" | "aggressive";
type ViewKey = "nl" | "json";

type Scenario = {
  key: string;
  label: string;
  subtitle: string;

  // What user edits (Words panel)
  intentNL: string;
  intentJSON: string;

  // Hidden compile source (NOT shown in UI)
  compileSourcePTN: string;

  // Trace “operator table” (what we render)
  traceOps: Array<{
    op: string;
    in: Record<string, any>;
    out: Record<string, any>;
  }>;
};

type TraceRow = {
  i: number;
  op: string;
  cu: number;
  ms: number;
  ok: boolean;
  inObj: Record<string, any>;
  outObj: Record<string, any>;
};

// ------------------------------ scenarios ------------------------------

const SCENARIOS: readonly Scenario[] = [
  {
    key: "doc-intel",
    label: "Document Intelligence",
    subtitle: "Scan → extract → brief → store → notify (with deterministic trace)",
    intentNL:
      'Scan the attached document, extract key entities (people, orgs, dates, money), summarize the top 5 points, file it under "Research/Briefs", then notify me with the summary and a link.',
    intentJSON: JSON.stringify(
      {
        task: "doc_intel",
        in: { doc: "$DOC", type: "pdf" },
        ops: [
          { extract: ["person", "org", "date", "money"] },
          { summarize: { top_k: 5 } },
          { file: { folder: "Research/Briefs" } },
          { notify: { include: ["summary", "link"] } },
        ],
        policy: { deterministic: true, trace: true },
      },
      null,
      2,
    ),
    compileSourcePTN: [
      "# hidden compile source (Photon/.ptn style)",
      '⊕ job "doc_intel" {',
      '  in pdf "$DOC";',
      "  ⊕ extract entities(person, org, date, money);",
      "  ⊕ summarize top 5;",
      '  ⊕ file to "Research/Briefs";',
      "  ⊕ notify include(summary, link);",
      "  ⊕ trace on;",
      "}",
    ].join("\n"),
    traceOps: [
      { op: "Π doc-intel:v1", in: { "$DOC": "paper.pdf" }, out: { run_id: "run_d94" } },
      { op: "ingest(doc)", in: { doc: "paper.pdf" }, out: { doc_id: "doc_1b2" } },
      {
        op: "extract(entities)",
        in: { fields: ["person", "org", "date", "money"] },
        out: { entities: 27 },
      },
      { op: "summarize(top5)", in: { top_k: 5 }, out: { bullets: 5 } },
      { op: "file(folder)", in: { folder: "Research/Briefs" }, out: { path: "/vault/briefs/doc_1b2" } },
      { op: "notify(inbox)", in: { include: ["summary", "link"] }, out: { message_id: "msg_88a" } },
    ],
  },
  {
    key: "ops-auto",
    label: "Compressed Intent → Action",
    subtitle: "Phrase → pipeline → outcome (trace + rollback)",
    intentNL:
      'When I say “ship it”, run tests, build, deploy to staging, then post the result to the team channel. If tests fail, open an issue with failing logs.',
    intentJSON: JSON.stringify(
      {
        trigger: "phrase:ship it",
        pipeline: ["tests", "build", "deploy(staging)", "notify(team)"],
        on_fail: ["open_issue(logs)"],
        policy: { deterministic: true, trace: true },
      },
      null,
      2,
    ),
    compileSourcePTN: [
      "# hidden compile source (Photon/.ptn style)",
      '⊕ trigger "ship it" {',
      "  ⊕ test ci;",
      "  ⊕ build;",
      '  ⊕ deploy "staging";',
      '  ⊕ notify "team" include(status, link);',
      "  ⊕ on_fail { open_issue include(logs, commit, stack); }",
      "  ⊕ trace on;",
      "}",
    ].join("\n"),
    traceOps: [
      { op: "Π ship-it:v1", in: { phrase: "ship it" }, out: { run_id: "run_2f1" } },
      { op: "tests(ci)", in: { suite: "ci" }, out: { pass: true, failures: 0 } },
      { op: "build()", in: { target: "web" }, out: { artifact: "staging.tar" } },
      { op: "deploy(staging)", in: { artifact: "staging.tar" }, out: { url: "https://staging.app" } },
      { op: "notify(team)", in: { include: ["status", "link"] }, out: { posted: true } },
    ],
  },
  {
    key: "ai-orch",
    label: "AI Orchestration (Policy + Trace)",
    subtitle: "Context → inference → verification (replayable decisions)",
    intentNL:
      "Take the user query, retrieve relevant context, generate an answer, then verify it against policy. Keep a replayable trace including the decision path.",
    intentJSON: JSON.stringify(
      {
        agent: "tessaris_orchestrator",
        steps: ["retrieve_context", "infer", "verify"],
        trace: { replayable: true, decisions: true },
        policy: { strict: true },
      },
      null,
      2,
    ),
    compileSourcePTN: [
      "# hidden compile source (Photon/.ptn style)",
      '⊕ agent "tessaris_orchestrator" {',
      '  in query "$Q";',
      "  ⊕ retrieve context;",
      "  ⊕ infer;",
      "  ⊕ verify policy;",
      "  ⊕ trace replay(decisions);",
      "}",
    ].join("\n"),
    traceOps: [
      { op: "Π orchestrate:v1", in: { "$Q": "user query" }, out: { run_id: "run_7aa" } },
      { op: "retrieve(context)", in: { db: "VectorDB" }, out: { hits: 12 } },
      { op: "infer()", in: { model: "Tessaris" }, out: { tokens: 428 } },
      { op: "verify(policy)", in: { mode: "strict" }, out: { pass: true } },
      { op: "emit(trace)", in: { replayable: true }, out: { trace_id: "GX-00C0FFEE" } },
    ],
  },
];

// ------------------------------ API (kept identical behavior to your original) ------------------------------

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

// ------------------------------ deterministic helpers ------------------------------

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

function buildTraceRows(seedStr: string, ops: Scenario["traceOps"], policy: PolicyKey): TraceRow[] {
  const seed = fnv1a(seedStr);
  const rng = makeRng(seed);

  const policyBias =
    policy === "conservative" ? 1.15 : policy === "aggressive" ? 0.85 : 1.0;

  return ops.map((o, idx) => {
    const cu = Math.max(3, Math.round((6 + rng() * 18) * policyBias));
    const ms = Math.max(12, Math.round((28 + rng() * 120) * policyBias));
    const okChance = policy === "aggressive" ? 0.92 : policy === "conservative" ? 0.985 : 0.96;
    const ok = rng() < okChance;

    return {
      i: idx + 1,
      op: o.op,
      cu,
      ms,
      ok,
      inObj: o.in,
      outObj: ok ? o.out : { error: "deterministic_abort", at: o.op },
    };
  });
}

function CodeLines({
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
  const text = value && value.length ? value : "—";
  const lines = useMemo(() => Math.max(minRows, text.split("\n").length), [text, minRows]);

  return (
    <div className="flex font-mono text-sm leading-6">
      <div className="select-none text-right text-gray-300 bg-white/40 border-r border-gray-100 px-4 py-4 min-w-[3rem]">
        {Array.from({ length: lines }, (_, i) => (
          <div key={i}>{i + 1}</div>
        ))}
      </div>

      {readOnly ? (
        <pre className="flex-1 whitespace-pre-wrap break-words px-4 py-4 text-gray-800">{text}</pre>
      ) : (
        <textarea
          value={value}
          onChange={(e) => onChange?.(e.target.value)}
          rows={lines}
          spellCheck={false}
          className="flex-1 resize-none bg-transparent px-4 py-4 outline-none text-gray-800"
        />
      )}
    </div>
  );
}

function Panel({
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
      <div className="px-8 py-6 border-b border-gray-100 flex items-start justify-between gap-4">
        <div>
          <div className="text-lg font-bold text-gray-800">{title}</div>
          {subtitle ? <div className="text-sm text-gray-400 mt-1">{subtitle}</div> : null}
        </div>
        {right ? <div className="pt-1">{right}</div> : null}
      </div>
      <div className="bg-[#fafafa]">{children}</div>
    </div>
  );
}

function Chip({ active, children, onClick }: { active?: boolean; children: React.ReactNode; onClick?: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`px-6 py-2 rounded-full text-sm font-semibold transition-all border ${
        active
          ? "bg-[#0071e3] text-white border-blue-600 shadow-md"
          : "bg-white text-gray-600 border-gray-200 hover:text-black"
      }`}
    >
      {children}
    </button>
  );
}

export default function GlyphOSWorkbench() {
  const [scenarioKey, setScenarioKey] = useState(SCENARIOS[0].key);
  const scenario = useMemo(() => SCENARIOS.find((s) => s.key === scenarioKey) || SCENARIOS[0], [scenarioKey]);

  const [view, setView] = useState<ViewKey>("nl");
  const [policy, setPolicy] = useState<PolicyKey>("deterministic");

  // user-editable words
  const [intentNL, setIntentNL] = useState(scenario.intentNL);
  const [intentJSON, setIntentJSON] = useState(scenario.intentJSON);

  // outputs
  const [glyphWire, setGlyphWire] = useState("—");
  const [traceRows, setTraceRows] = useState<TraceRow[]>([]);
  const [traceId, setTraceId] = useState("—");

  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const loadScenario = (s: Scenario) => {
    setScenarioKey(s.key);
    setIntentNL(s.intentNL);
    setIntentJSON(s.intentJSON);
    setGlyphWire("—");
    setTraceRows([]);
    setTraceId("—");
    setErr(null);
  };

  const run = async () => {
    try {
      setBusy(true);
      setErr(null);

      // compile hidden Photon source -> glyph wire (this keeps the demo "real" without showing .ptn UI)
      const resp = await translateToGlyphs(scenario.compileSourcePTN, "photon");
      const wire = (resp.translated ?? "").trim() || "—";
      setGlyphWire(wire);

      const seedStr = `${scenario.key}::${policy}::${wire}::${intentNL.length}::${intentJSON.length}`;
      const rows = buildTraceRows(seedStr, scenario.traceOps, policy);
      setTraceRows(rows);
      setTraceId(`GX-${fnv1a(seedStr).toString(16).padStart(8, "0").toUpperCase()}`);
    } catch (e: any) {
      setErr(e?.message || "Run failed");
    } finally {
      setBusy(false);
    }
  };

  const replay = () => {
    if (!glyphWire || glyphWire === "—") return;
    const seedStr = `${scenario.key}::${policy}::${glyphWire}::${intentNL.length}::${intentJSON.length}`;
    const rows = buildTraceRows(seedStr, scenario.traceOps, policy);
    setTraceRows(rows);
    setTraceId(`GX-${fnv1a(seedStr).toString(16).padStart(8, "0").toUpperCase()}`);
  };

  return (
    <section className="space-y-16">
      {/* BIG hero (match old sizing) */}
        <div className="text-center space-y-6">
        <h1 className="text-7xl md:text-9xl font-bold tracking-tight text-black italic">
            Glyph OS
        </h1>

        <p className="text-2xl text-gray-500 font-light tracking-tight">
            The Language of Symbols.{" "}
            <span className="text-black font-medium">The Speed of Light.</span>
        </p>

        <p className="max-w-2xl mx-auto text-lg text-gray-500 leading-relaxed">
            An operating system built in symbols, executing at the speed of thought,
            compressed for the next era of cognition.
        </p>
        </div>

      {/* Workbench */}
      <div className="w-full bg-white rounded-[3rem] shadow-2xl shadow-gray-200/60 border border-gray-100 p-10 md:p-12 space-y-10">
        {/* Presets header (like your “Demo Presets” layout) */}
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-8">
          <div>
            <div className="text-xs font-bold text-gray-300 uppercase tracking-widest">Demo Presets</div>
            <div className="text-3xl font-bold text-gray-900 mt-2">{scenario.label}</div>
            <div className="text-gray-500 mt-2">{scenario.subtitle}</div>
          </div>

          <div className="flex flex-wrap gap-3 justify-start lg:justify-end py-3">
            {SCENARIOS.map((s) => (
              <Chip key={s.key} active={s.key === scenarioKey} onClick={() => loadScenario(s)}>
                {s.label}
              </Chip>
            ))}
          </div>
        </div>

        {/* Policy + Run row */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
          <div className="flex flex-wrap items-center gap-3">
            <div className="text-xs font-bold text-gray-300 uppercase tracking-widest mr-2">Policy</div>
            <Chip active={policy === "deterministic"} onClick={() => setPolicy("deterministic")}>
              Deterministic
            </Chip>
            <Chip active={policy === "conservative"} onClick={() => setPolicy("conservative")}>
              Conservative
            </Chip>
            <Chip active={policy === "aggressive"} onClick={() => setPolicy("aggressive")}>
              Aggressive
            </Chip>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={replay}
              className="px-8 py-3 rounded-full text-sm font-semibold bg-white border border-gray-200 text-gray-700 hover:text-black transition"
            >
              Replay
            </button>
            <button
              type="button"
              onClick={run}
              disabled={busy}
              className={`px-10 py-3 rounded-full text-sm font-semibold transition-all ${
                busy ? "bg-gray-200 text-gray-500" : "bg-[#0071e3] text-white shadow-md hover:brightness-110"
              }`}
            >
              {busy ? "Running…" : "Run"}
            </button>
          </div>
        </div>

        {err ? <div className="text-sm text-red-600 whitespace-pre-wrap">{err}</div> : null}

        {/* ✅ 3 REQUIRED PANELS (wide, not squashed) */}
        <div className="grid lg:grid-cols-3 gap-8">
          {/* Words */}
          <Panel
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
            <div className="p-6">
              {view === "nl" ? (
                <textarea
                  value={intentNL}
                  onChange={(e) => setIntentNL(e.target.value)}
                  className="w-full min-h-[260px] rounded-[2rem] border border-gray-200 bg-white p-5 text-sm text-gray-800 leading-relaxed outline-none focus:ring-2 focus:ring-blue-200"
                  spellCheck={false}
                />
              ) : (
                <div className="rounded-[2rem] border border-gray-100 bg-white overflow-hidden">
                  <CodeLines value={intentJSON} onChange={setIntentJSON} minRows={14} />
                </div>
              )}
            </div>
          </Panel>

          {/* Glyph-wire */}
          <Panel
            title="Glyph-wire"
            subtitle="Canonical meaning-shape (portable + stable)"
            right={
              <div className="text-[11px] font-bold uppercase tracking-widest text-[#0071e3]">
                Small • Stable • Replayable
              </div>
            }
          >
            <div className="p-6">
              <div className="rounded-[2rem] border border-blue-100 bg-blue-50/40 overflow-hidden">
                <CodeLines value={glyphWire} readOnly minRows={14} />
              </div>
            </div>
          </Panel>

          {/* Trace */}
          <Panel
            title="Trace"
            subtitle="Deterministic execution + audit trail"
            right={
              <div className="text-[11px] font-bold uppercase tracking-widest text-gray-400">
                Trace ID: {traceId}
              </div>
            }
          >
            <div className="p-6 space-y-4">
              {traceRows.length === 0 ? (
                <div className="text-sm text-gray-400">Press Run to generate a deterministic trace.</div>
              ) : (
                <div className="space-y-4">
                  {traceRows.map((r) => (
                    <div
                      key={r.i}
                      className="bg-white rounded-[2rem] border border-gray-100 shadow-sm p-5 space-y-4"
                    >
                      <div className="flex items-center justify-between gap-4">
                        <div className="flex items-center gap-3">
                          <div className="text-gray-400 font-mono text-xs">{r.i}</div>
                          <div className="text-base font-semibold text-gray-900">{r.op}</div>
                          <div className={`text-xs font-bold ${r.ok ? "text-emerald-600" : "text-rose-600"}`}>
                            {r.ok ? "OK" : "FAIL"}
                          </div>
                        </div>
                        <div className="flex items-center gap-4 text-xs font-mono text-gray-400">
                          <span>{r.cu} cu</span>
                          <span>{r.ms} ms</span>
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-4">
                        <div className="rounded-2xl border border-gray-100 bg-[#fafafa] p-4">
                          <div className="text-[10px] font-bold uppercase tracking-widest text-gray-400 mb-2">IN</div>
                          <pre className="text-[11px] font-mono text-gray-700 whitespace-pre-wrap break-words">
                            {JSON.stringify(r.inObj, null, 2)}
                          </pre>
                        </div>

                        <div className="rounded-2xl border border-gray-100 bg-[#fafafa] p-4">
                          <div className="text-[10px] font-bold uppercase tracking-widest text-gray-400 mb-2">OUT</div>
                          <pre className="text-[11px] font-mono text-gray-700 whitespace-pre-wrap break-words">
                            {JSON.stringify(r.outObj, null, 2)}
                          </pre>
                        </div>
                      </div>
                    </div>
                  ))}

                  <div className="text-xs text-gray-400 pt-1">
                    Same intent + same policy ⇒ same wire + same trace.
                  </div>
                </div>
              )}
            </div>
          </Panel>
        </div>
      </div>

      <div className="text-center font-medium text-gray-400 italic">“Same meaning. Less noise. Faster execution.”</div>
    </section>
  );
}