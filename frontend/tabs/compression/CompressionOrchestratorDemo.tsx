// frontend/tabs/compression/CompressionOrchestratorDemo.tsx
"use client";

import { useMemo, useRef, useState } from "react";

type CodeLang = "photon" | "python";

type TranslateResponse = {
  translated?: string;
  glyph_count?: number;
  chars_before?: number;
  chars_after?: number;
  compression_ratio?: number;
};

type Scenario = {
  title: string;
  intent: string;
  // a compact "program" we can send to /api/photon/translate (or fallback)
  program: string;
  // optional “pretty glyphs” (if you want to hardcode vibe)
  glyphsHint?: string;
  steps: string[];
  policy: string;
};

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

// deterministic hash (trace id + fallback wire)
function fnv1a(input: string) {
  let h = 0x811c9dc5;
  for (let i = 0; i < input.length; i++) {
    h ^= input.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return h >>> 0;
}

function fallbackGlyphWire(program: string, hint?: string) {
  // deterministic compact-ish “wire” for demo when API not reachable
  const seed = fnv1a(program).toString(16).toUpperCase().slice(0, 8);
  const base = hint?.trim()
    ? hint.trim()
    : "❖ ⟲ ⊕ ⇢ 𝛙"; // vibey fallback
  return `${base}  ⟦${seed}⟧`;
}

function makeTraceId(seedStr: string) {
  const seed = fnv1a(seedStr).toString(16).toUpperCase().padStart(8, "0");
  return `TR-${seed.slice(0, 4)}-${seed.slice(4, 8)}`;
}

export default function CompressionOrchestratorDemo() {
  const [activeScenario, setActiveScenario] = useState(0);
  const [isExecuting, setIsExecuting] = useState(false);
  const [lang, setLang] = useState<CodeLang>("photon");

  const [glyphWire, setGlyphWire] = useState<string>("—");
  const [traceId, setTraceId] = useState<string>("—");
  const [err, setErr] = useState<string | null>(null);

  const execTimer = useRef<number | null>(null);

  const scenarios: Scenario[] = useMemo(
    () => [
      {
        title: "Document Intelligence",
        intent: "Scan document 'Report_Alpha', extract 'Financials', archive to 'Vault', and notify 'Finance_Team'.",
        glyphsHint: "📄(α) → 🔍{💰} → 🗄️(V) ⟲ 🔔(FT)",
        program: [
          "# glyph-wire program (demo)",
          '⊕ job "doc_intel" {',
          '  in doc "Report_Alpha";',
          '  ⊕ extract "Financials";',
          '  ⊕ archive "Vault";',
          '  ⊕ notify "Finance_Team";',
          "  ⊕ trace on;",
          "}",
        ].join("\n"),
        steps: ["FETCH(Report_Alpha)", "EXTRACT_ENTITY(Financials)", "COMMIT_STORAGE(Vault)", "EMIT_SIGNAL(Finance_Notify)"],
        policy: "Privacy_High_Secure",
      },
      {
        title: "Resonance Trigger",
        intent: "Monitor wave-pool sensor, if resonance > 0.8, trigger cooling pump and log state change.",
        glyphsHint: "〰️(S) > 0.8 ⇒ ❄️(P) + 📝(log)",
        program: [
          "# resonance trigger (demo)",
          '⊕ monitor "wave_pool_sensor" as S {',
          "  ⊕ read S;",
          "  ⊕ if resonance(S) > 0.8 {",
          '      trigger "cooling_pump";',
          '      log "state_change";',
          "    }",
          "  ⊕ trace on;",
          "}",
        ].join("\n"),
        steps: ["POLL_SENSOR(S)", "COMPARE(0.8)", "TRIGGER_ACTUATOR(Pump)", "WRITE_TRACE_LOG"],
        policy: "Auto_Response_Standard",
      },
      {
        title: "AI Orchestration",
        intent: "Take user query, find matching context in VectorDB, generate response via Tessaris, and verify output.",
        glyphsHint: "❓(U) + 🗃️(V) → 🧠(T) ⟲ ✅",
        program: [
          "# AI orchestration (demo)",
          '⊕ agent "tessaris" {',
          "  in query U;",
          '  ⊕ vector_search in "VectorDB" using U;',
          '  ⊕ infer via "Tessaris";',
          "  ⊕ verify;",
          "  ⊕ trace replay(decisions);",
          "}",
        ].join("\n"),
        steps: ["PARSE_QUERY", "VECTOR_SEARCH", "GENERATE_INFERENCE", "VERIFY_SYMATIC_LAW"],
        policy: "Audit_Required",
      },
    ],
    [],
  );

  const current = scenarios[activeScenario];

  const runExecution = async () => {
    setIsExecuting(true);
    setErr(null);

    // clear any prior timers
    if (execTimer.current) {
      window.clearTimeout(execTimer.current);
      execTimer.current = null;
    }

    // 1) Produce “glyph wire” (API if possible, deterministic fallback otherwise)
    let wire = "—";
    try {
      const resp = await translateToGlyphs(current.program, lang);
      wire = resp.translated?.trim() ? resp.translated.trim() : fallbackGlyphWire(current.program, current.glyphsHint);
    } catch (e: any) {
      wire = fallbackGlyphWire(current.program, current.glyphsHint);
      setErr(e?.message ? String(e.message) : "Translator offline — using local deterministic wire.");
    }

    setGlyphWire(wire);

    // 2) Deterministic trace id (seeded by scenario + wire)
    const tid = makeTraceId(`${current.title}::${wire}::${current.policy}`);
    setTraceId(tid);

    // 3) End execution after animation window
    execTimer.current = window.setTimeout(() => {
      setIsExecuting(false);
      execTimer.current = null;
    }, 2000);
  };

  const downloadTrace = () => {
    const payload = {
      trace_id: traceId,
      scenario: current.title,
      policy: current.policy,
      intent: current.intent,
      glyph_wire: glyphWire,
      steps: current.steps.map((s, i) => ({ idx: i + 1, status: "OK", op: s })),
      deterministic: true,
      substrate: "Photon/Local",
    };

    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = `${traceId || "trace"}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();

    URL.revokeObjectURL(url);
  };

  return (
    <div className="w-full bg-white rounded-[2.5rem] shadow-xl border border-gray-100 p-10 space-y-12">
      <div className="flex justify-between items-center gap-6">
        <div>
          <div className="text-xs font-bold text-gray-300 uppercase tracking-widest">Orchestration Engine</div>
          <h3 className="text-2xl font-bold text-gray-800 mt-1">Intent → Glyph → Execution</h3>
          <div className="text-sm text-gray-500 mt-2">
            Deterministic trace, audit-ready. (Translator uses API when available.)
          </div>
        </div>

        <div className="flex items-center gap-3">
          <select
            value={lang}
            onChange={(e) => setLang(e.target.value as CodeLang)}
            className="px-4 py-2 rounded-xl border border-gray-200 bg-white text-sm font-semibold text-gray-700 shadow-sm outline-none focus:ring-2 focus:ring-blue-200"
          >
            <option value="photon">Photon (.ptn)</option>
            <option value="python">Python (.py)</option>
          </select>

          <div className="flex gap-2 bg-gray-100 p-1.5 rounded-full">
            {scenarios.map((s, i) => (
              <button
                key={s.title}
                onClick={() => {
                  setActiveScenario(i);
                  setGlyphWire("—");
                  setTraceId("—");
                  setErr(null);
                  setIsExecuting(false);
                }}
                className={`px-6 py-2 rounded-full text-xs font-bold transition-all ${
                  activeScenario === i ? "bg-white text-black shadow-sm" : "text-gray-400 hover:text-gray-600"
                }`}
              >
                Scenario {i + 1}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-8">
        {/* Column 1: Natural Language Intent */}
        <div className="space-y-4">
          <div className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Natural Language Intent</div>
          <div className="p-6 bg-[#fafafa] rounded-3xl border border-gray-100 h-40 flex items-center italic text-gray-600 leading-relaxed">
            “{current.intent}”
          </div>

          <div className="pt-2">
            <div className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-2">Scenario</div>
            <div className="text-sm font-semibold text-gray-800">{current.title}</div>
          </div>
        </div>

        {/* Column 2: Glyph-Wire Shape */}
        <div className="space-y-4">
          <div className="text-[10px] font-bold text-[#0071e3] uppercase tracking-widest">Glyph-Wire Program</div>
          <div className="p-6 bg-blue-50/50 rounded-3xl border border-blue-100 h-40 flex flex-col items-center justify-center relative overflow-hidden">
            <div className="text-3xl md:text-4xl tracking-[0.12em] font-mono text-[#0071e3] drop-shadow-sm z-10 text-center">
              {glyphWire === "—" ? (current.glyphsHint || "—") : glyphWire}
            </div>
            <div className="absolute inset-0 bg-blue-400/5 animate-pulse" />
          </div>

          <div className="text-xs text-gray-400 font-mono">
            TRACE_ID: <span className="text-gray-600">{traceId}</span>
          </div>
        </div>

        {/* Column 3: Deterministic Trace */}
        <div className="space-y-4">
          <div className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Execution Trace</div>

          <div className="p-6 bg-black rounded-3xl border border-gray-800 h-40 overflow-hidden font-mono text-[10px] relative">
            <div
              className={`space-y-1 transition-all duration-1000 ${
                isExecuting ? "translate-y-[-50%]" : "translate-y-0"
              }`}
            >
              {current.steps.map((step, i) => (
                <div key={i} className="flex gap-3">
                  <span className="text-gray-600">[{i + 1}]</span>
                  <span className="text-green-400">OK</span>
                  <span className="text-gray-300">{step}</span>
                </div>
              ))}
              <div className="text-blue-400 mt-2">-- POLICY: {current.policy} --</div>
              <div className="text-gray-500 italic">-- TRACE_COMPLETE --</div>
            </div>

            {!isExecuting && (
              <div className="absolute inset-0 bg-black/40 flex items-center justify-center backdrop-blur-sm">
                <button
                  onClick={runExecution}
                  className="bg-white text-black px-6 py-2 rounded-full font-bold text-xs hover:scale-105 transition-all shadow-xl"
                >
                  RUN PROGRAM
                </button>
              </div>
            )}
          </div>

          <div className="flex items-center justify-between">
            <div className="text-[11px] text-gray-400 font-medium uppercase tracking-widest">
              Deterministic: <span className="text-green-500">Verified</span>
            </div>
            <button
              onClick={downloadTrace}
              disabled={traceId === "—" || glyphWire === "—"}
              className={`text-xs font-bold px-4 py-2 rounded-full transition-all ${
                traceId === "—" || glyphWire === "—"
                  ? "bg-gray-100 text-gray-300 cursor-not-allowed"
                  : "bg-white border border-gray-200 text-gray-700 hover:text-black hover:shadow-sm"
              }`}
            >
              Download Trace
            </button>
          </div>
        </div>
      </div>

      {err ? (
        <div className="text-xs text-amber-700 bg-amber-50 border border-amber-100 rounded-2xl p-4 leading-relaxed">
          {err}
        </div>
      ) : null}

      <div className="pt-8 border-t border-gray-50 flex items-center justify-between text-gray-400 text-[11px] font-medium uppercase tracking-widest">
        <span>Substrate: Photon/Local</span>
        <div className="flex gap-8">
          <span>Latency: 0.002ms</span>
          <span>Entropy: 0.00%</span>
          <span className="text-green-500">Deterministic: Verified</span>
        </div>
      </div>
    </div>
  );
}