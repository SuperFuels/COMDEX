// frontend/pages/index.tsx
"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { NextPage } from "next";

/**
 * ⚠️ NOTE: QFC is currently disabled to prevent the useQFCFocus error
 * breaking the demo until the Provider is implemented.
 */

type CodeLang = "photon" | "python";

type TranslateResponse = {
  translated?: string;
  glyph_count?: number;
  chars_before?: number;
  chars_after?: number;
  compression_ratio?: number;
};

// ✅ Use configured API base when present (works in dev + prod),
// ✅ otherwise fall back to same-origin (/api) which your Next rewrite proxies.
const API_BASE =
  (typeof window !== "undefined" && (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/+$/, "")) || "";

// ✅ Build URL robustly (avoids double slashes, works with trailingSlash=true)
function apiUrl(path: string) {
  if (!path.startsWith("/")) path = `/${path}`;
  // If NEXT_PUBLIC_API_URL is set, call it directly; else rely on Next rewrite at /api/*
  return API_BASE ? `${API_BASE}${path}` : path;
}

async function translateToGlyphs(code: string, lang: CodeLang): Promise<TranslateResponse> {
  // ✅ Match your FastAPI photon_api.py exactly:
  // POST /api/photon/translate  body: { text, language }
  const res = await fetch(apiUrl("/api/photon/translate"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      text: code,
      language: lang,
    }),
  });

  if (!res.ok) {
    const ct = res.headers.get("content-type") || "";
    const raw = await res.text().catch(() => "");

    // Helpful diagnostics for the two common failure modes:
    // - HTML response => you hit Next/another server, not FastAPI (rewrite/env)
    // - 404/405 => wrong base URL, wrong rewrite, or method not allowed
    const hint = ct.includes("text/html")
      ? "HTML response — likely not hitting FastAPI. Check next.config.js rewrites for /api/:path* and NEXT_PUBLIC_API_URL."
      : "";

    const msg = (raw && raw.slice(0, 400)) || res.statusText;
    throw new Error(`HTTP ${res.status} — ${msg}${hint ? `\n${hint}` : ""}`);
  }

  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return (await res.json()) as TranslateResponse;

  // If backend ever returns plain text, accept it too.
  const text = await res.text();
  return { translated: text, chars_before: code.length, chars_after: text.length };
}

const Home: NextPage = () => {
  const [activeTab, setActiveTab] = useState<"glyph" | "symatics">("glyph");

  return (
    <div className="min-h-screen bg-[#f5f5f7] text-[#1d1d1f] selection:bg-blue-100 font-sans antialiased">
      <div className="h-screen overflow-y-auto">
        <main className="relative z-10 flex flex-col items-center justify-start min-h-full px-6 max-w-5xl mx-auto py-16 pb-32">
          {/*  Minimalist Tab Switcher (sticky) */}
          <nav className="mb-16 p-1 bg-white/70 backdrop-blur-md border border-gray-200 rounded-full flex gap-1 shadow-sm sticky top-4 z-50">
            <button
              onClick={() => setActiveTab("glyph")}
              className={`px-10 py-2.5 rounded-full text-sm font-medium transition-all duration-300 ${
                activeTab === "glyph"
                  ? "bg-[#0071e3] text-white shadow-md"
                  : "text-gray-500 hover:text-black"
              }`}
            >
              Glyph OS
            </button>
            <button
              onClick={() => setActiveTab("symatics")}
              className={`px-10 py-2.5 rounded-full text-sm font-medium transition-all duration-300 ${
                activeTab === "symatics"
                  ? "bg-[#0071e3] text-white shadow-md"
                  : "text-gray-500 hover:text-black"
              }`}
            >
              Symatics
            </button>
          </nav>

          <div className="w-full">
            {/* GLYPH TAB */}
            {activeTab === "glyph" && (
              <section className="animate-in fade-in zoom-in-95 duration-700 space-y-16">
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

                <div className="grid md:grid-cols-2 gap-10">
                  <ComparisonCard
                    title="Culinary Logic"
                    traditional="Get eggs, crack, whisk, heat pan, add butter, cook, and plate."
                    glyph="🥚 → 🍳 → 🍽️"
                    labels="Ingredients → Cook → Serve"
                  />
                  <ComparisonCard
                    title="Document Intelligence"
                    traditional="Open document, scan for key points, extract data, summarize, and file."
                    glyph="📄 → ✨ → 🗂️"
                    labels="Input → Intelligence → Archive"
                  />
                </div>

                <div className="text-center font-medium text-gray-400">“Same result. Less noise.”</div>
                <GlyphTranslateDemo />
              </section>
            )}

            {/* SYMATICS TAB */}
            {activeTab === "symatics" && (
              <section className="animate-in fade-in zoom-in-95 duration-700 space-y-16">
                <div className="text-center space-y-6">
                  <h1 className="text-7xl md:text-9xl font-bold tracking-tight text-black italic">
                    Symatics
                  </h1>
                  <p className="text-2xl text-gray-500 font-light tracking-tight">
                    Start with{" "}
                    <span className="text-[#0071e3] font-medium uppercase">patterns</span>, not numbers.
                  </p>
                </div>

                {/* Core Equation Hero */}
                <div className="bg-white rounded-[3rem] p-16 text-center shadow-xl shadow-gray-200/50 border border-gray-100">
                  <div className="text-8xl mb-12 tracking-widest flex justify-center items-center gap-8">
                    <span className="font-mono text-gray-800">〰️</span>
                    <span className="text-4xl text-gray-300 font-light">+</span>
                    <span className="font-mono text-gray-800">〰️</span>
                    <span className="text-4xl text-gray-300 font-light">=</span>
                    <div className="relative inline-flex items-center justify-center">
                      <span className="font-mono text-[#0071e3] drop-shadow-sm">〰️</span>
                      <span className="absolute -right-8 flex items-center justify-center w-14 h-14 rounded-full border-[3px] border-[#0071e3] text-[#0071e3] text-3xl font-bold bg-white shadow-sm">
                        R
                      </span>
                    </div>
                  </div>

                  <p className="text-gray-500 text-xl max-w-2xl mx-auto leading-relaxed">
                    〰️ + 〰️ = 〰️® is a breakthrough in <span className="text-black font-semibold">qualitative state change</span>.
                  </p>
                </div>

                {/* Text Explainer Container */}
                <div className="bg-white rounded-[3rem] shadow-xl shadow-gray-200/50 border border-gray-100 overflow-hidden">
                  <div className="p-10 md:p-12">
                    <div className="max-w-3xl mx-auto text-left bg-[#fafafa] rounded-3xl p-8 border border-gray-100">
                      <div className="text-xs font-bold text-gray-300 uppercase tracking-widest mb-4">
                        The New Logic of Resonance
                      </div>

                      <p className="text-gray-600 leading-relaxed text-lg">
                        <span className="font-semibold text-gray-800">
                          Beyond Counting: Moving from Quantity to Quality
                        </span>
                        <br />
                        In the world we know, math is for accounting. If you have one dollar and add
                        another, you have two. This is the logic of accumulation—simply having "more of the same."
                      </p>

                      <div className="mt-8 space-y-4 border-l-2 border-gray-200 pl-6">
                        <div>
                          <span className="font-semibold text-gray-800">Traditional Math:</span>{" "}
                          <span className="font-mono bg-gray-100 px-3 py-1 rounded text-sm text-gray-600">1 + 1 = 2</span>
                        </div>

                        <div className="pt-2">
                          <span className="font-semibold text-[#0071e3]">Symatic Logic:</span>{" "}
                          <span className="font-mono bg-blue-50 text-[#0071e3] px-3 py-1 rounded text-sm">〰️ + 〰️ = 〰️®</span>
                          <div className="text-gray-500 text-sm mt-1 ml-1">This is the logic of harmony—where patterns combine to create a new, superior reality.</div>
                        </div>
                      </div>

                      <div className="mt-12">
                        <div className="font-semibold text-gray-800 text-xl mb-4">The Story of the "Spark"</div>
                        <p className="text-gray-600 leading-relaxed">
                          Imagine two people swinging a jump rope. If they move their arms randomly, the rope tangles. But if they move in perfect rhythm, the rope forms a powerful, stable arc. 
                        </p>
                        <div className="mt-8 space-y-4">
                          <div className="bg-white p-5 rounded-2xl border border-gray-100 shadow-sm flex gap-4 items-start">
                            <span className="text-2xl mt-1 text-gray-800">〰️</span>
                            <div>
                              <span className="font-bold text-gray-800 block">The Wave</span>
                              <p className="text-gray-600 text-sm">Raw energy, data, or intent in motion looking for its rhythm.</p>
                            </div>
                          </div>
                          <div className="bg-white p-5 rounded-2xl border border-blue-100 shadow-sm flex gap-4 items-start">
                            <span className="text-2xl mt-1 text-[#0071e3]">〰️®</span>
                            <div>
                              <span className="font-bold text-[#0071e3] block">Resonance State</span>
                              <p className="text-gray-600 text-sm">When patterns lock together, they amplify into a result greater than the sum of its parts.</p>
                            </div>
                          </div>
                        </div>

                        <div className="mt-12 pt-8 border-t border-gray-200">
                          <div className="font-bold text-gray-800 text-lg mb-3">Why It Matters</div>
                          <p className="text-gray-600 leading-relaxed">
                            When your intent (〰️) perfectly aligns with the system (〰️), the noise
                            of the world disappears. You are achieving Resonance (⟲).
                          </p>
                          <div className="mt-8 text-gray-800 font-medium text-center py-8 bg-white rounded-2xl border border-gray-100 shadow-inner italic text-lg px-6">
                            “Symatics doesn't just count the world. It oscillates it into harmony.”
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <ResonanceWorkbench />

                <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                  {["〰️ Wave", "💡 Photon", "⊕ Superpose", "↔ Entangle", "⟲ Resonance", "∇ Collapse", "⇒ Trigger"].map(
                    (op) => (
                      <div
                        key={op}
                        className="p-5 bg-white rounded-2xl text-center shadow-sm border border-gray-100 hover:shadow-md transition-all cursor-default"
                      >
                        <span className="text-sm font-semibold text-gray-700">{op}</span>
                      </div>
                    ),
                  )}
                </div>
              </section>
            )}
          </div> {/* Correct closing tag for w-full */}

          {/* DOCUMENT READER SECTION */}
          <section className="w-full mt-32 animate-in fade-in slide-in-from-bottom-8 duration-1000">
            <div className="flex flex-col gap-8">
              <div className="flex justify-between items-end border-b border-gray-200 pb-6">
                <div>
                  <h2 className="text-3xl font-bold tracking-tight text-black">Technical Papers</h2>
                  <p className="text-gray-500 mt-2">Active Document: <span className="text-[#0071e3] font-mono">symatics_full_technical_document.mdx</span></p>
                </div>
                <button className="text-sm font-semibold text-[#0071e3] hover:underline px-4 py-2 bg-blue-50 rounded-full">
                  Download PDF Original
                </button>
              </div>

              {/* The MDX Paper Container */}
              <div className="bg-white rounded-[3rem] shadow-2xl shadow-gray-200/50 border border-gray-100 overflow-hidden relative">
                {/* Progress Bar (Visual Only for now) */}
                <div className="absolute top-0 left-0 w-full h-1 bg-gray-100">
                  <div className="h-full bg-[#0071e3] w-1/3 shadow-[0_0_10px_#0071e3]" />
                </div>

                <div className="p-12 md:p-20 prose prose-slate max-w-none">
                  {/* The MDX content will render here. 
                      I've added the "Blue Glow" logic via CSS classes in step 3 */}
                  <div className="symatics-paper-view">
                    {/* For the build to work immediately, we'll placeholder the component 
                        until you finish the MDX config in step 2 */}
                    <div className="text-center py-20">
                      <div className="animate-pulse flex flex-col items-center">
                        <div className="h-4 w-48 bg-gray-200 rounded mb-4"></div>
                        <div className="h-4 w-64 bg-gray-100 rounded"></div>
                        <p className="mt-8 text-gray-400 font-medium">Initializing Symatic Document Engine...</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* CTA */}
          <footer className="mt-24 flex gap-6">
            <button className="px-12 py-4 bg-black text-white rounded-full font-semibold text-lg hover:bg-gray-800 transition-all">
              Launch GlyphNet
            </button>
            <button className="px-12 py-4 border-2 border-black text-black rounded-full font-semibold text-lg hover:bg-black hover:text-white transition-all">
              View Multiverse
            </button>
          </footer>
        </main>
      </div>

      {/* HUD */}
      <div className="fixed bottom-8 right-8 p-4 bg-white/80 border border-gray-200 rounded-2xl backdrop-blur-xl text-[11px] font-bold text-gray-400 tracking-wider shadow-lg">
        <div className="flex gap-6 uppercase">
          <span>Space: Pause</span>
          <span>1-4: Glyph</span>
          <span>5-8: Symatics</span>
          <span className="text-[#0071e3]">R: Restart</span>
        </div>
      </div>
    </div>
  );
};

/* ---------------------------- SYMATICS MINI DEMO ---------------------------- */

const ResonanceWorkbench = () => {
  const [paused, setPaused] = useState(false);
  const [amplitude, setAmplitude] = useState(18);
  const [cycles, setCycles] = useState(6);
  const [speed, setSpeed] = useState(1);

  // time in radians
  const [t, setT] = useState(0);
  const rafRef = useRef<number | null>(null);
  const lastRef = useRef<number>(0);

  useEffect(() => {
    if (paused) return;

    const loop = (now: number) => {
      const last = lastRef.current || now;
      const dt = (now - last) / 1000;
      lastRef.current = now;

      // stable-ish motion: radians advance
      setT((prev) => prev + dt * speed * 2.2);

      rafRef.current = requestAnimationFrame(loop);
    };

    rafRef.current = requestAnimationFrame(loop);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    };
  }, [paused, speed]);

  return (
    <div className="w-full bg-white rounded-[2.5rem] shadow-xl border border-gray-100 p-10 space-y-10">
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-8">
        <div>
          <div className="text-xs font-bold text-gray-300 uppercase tracking-widest">
            Wave Interference
          </div>
          <h3 className="text-xl font-semibold text-gray-800 mt-1">
            Constructive vs Destructive (A, B, and A+B)
          </h3>
          <p className="text-sm text-gray-500 mt-2">
            Toggle motion, then adjust amplitude / frequency to see how superposition changes the
            combined result.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setPaused((p) => !p)}
            className={`px-5 py-2 rounded-full text-sm font-semibold transition-all ${
              paused
                ? "bg-[#0071e3] text-white shadow-md hover:brightness-110"
                : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            }`}
          >
            {paused ? "Play" : "Pause"}
          </button>
          <div className="text-xs text-gray-400 font-bold uppercase tracking-widest">
            {paused ? "stopped" : "running"}
          </div>
        </div>
      </div>

      {/* Controls */}
      <div className="grid md:grid-cols-3 gap-6">
        <Slider
          label="Amplitude"
          value={amplitude}
          min={8}
          max={28}
          step={1}
          onChange={setAmplitude}
          suffix="px"
        />
        <Slider
          label="Frequency"
          value={cycles}
          min={3}
          max={9}
          step={1}
          onChange={setCycles}
          suffix="cycles"
        />
        <Slider
          label="Speed"
          value={speed}
          min={0}
          max={3}
          step={0.1}
          onChange={setSpeed}
          suffix="×"
        />
      </div>

      {/* Panels (screenshot-style) */}
      <div className="grid md:grid-cols-2 gap-10">
        <WavePanel title="constructive interference" t={t} amplitude={amplitude} cycles={cycles} phaseB={0} />
        <WavePanel
          title="destructive interference"
          t={t}
          amplitude={amplitude}
          cycles={cycles}
          phaseB={Math.PI}
        />
      </div>
    </div>
  );
};

const Slider = ({
  label,
  value,
  min,
  max,
  step,
  onChange,
  suffix,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (v: number) => void;
  suffix?: string;
}) => (
  <div className="space-y-3">
    <label className="flex justify-between text-sm font-medium text-gray-500">
      <span>{label}</span>
      <span className="font-mono italic">
        {typeof value === "number" ? value.toFixed(step < 1 ? 1 : 0) : value}
        {suffix ? ` ${suffix}` : ""}
      </span>
    </label>
    <input
      type="range"
      min={min}
      max={max}
      step={step}
      value={value}
      onChange={(e) => onChange(parseFloat(e.target.value))}
      className="w-full h-1.5 bg-gray-100 rounded-lg appearance-none cursor-pointer accent-blue-600"
    />
  </div>
);

const WavePanel = ({
  title,
  t,
  amplitude,
  cycles,
  phaseB,
}: {
  title: string;
  t: number;
  amplitude: number;
  cycles: number;
  phaseB: number;
}) => {
  return (
    <div className="bg-[#fafafa] rounded-3xl p-8 border border-gray-100">
      <div className="text-2xl md:text-3xl font-semibold text-gray-700 tracking-tight mb-8">
        {title}
      </div>

      <div className="space-y-8">
        <WaveRow
          label="wave A"
          color="rgb(185 28 28)"
          t={t}
          amplitude={amplitude}
          cycles={cycles}
          phase={0}
          mode="single"
        />

        <WaveRow
          label="wave B"
          color="rgb(13 148 136)"
          t={t}
          amplitude={amplitude}
          cycles={cycles}
          phase={phaseB}
          mode="single"
        />

        <WaveRow
          label="wave A+B"
          color="rgb(124 58 237)"
          t={t}
          amplitude={amplitude}
          cycles={cycles}
          phase={phaseB}
          mode="sum"
        />
      </div>
    </div>
  );
};

const WaveRow = ({
  label,
  color,
  t,
  amplitude,
  cycles,
  phase,
  mode,
}: {
  label: string;
  color: string;
  t: number;
  amplitude: number;
  cycles: number;
  phase: number;
  mode: "single" | "sum";
}) => {
  const width = 520;
  const height = 80;
  const mid = height / 2;

  const points = 140;
  const twoPi = Math.PI * 2;

  const d = useMemo(() => {
    let path = "";
    for (let i = 0; i <= points; i++) {
      const x = (i / points) * width;
      const theta = (x / width) * cycles * twoPi;

      const a = Math.sin(theta + t);
      const b = Math.sin(theta + phase + t);

      const v = mode === "sum" ? a + b : b;
      const y = mid - v * amplitude;

      if (i === 0) path += `M ${x.toFixed(2)} ${y.toFixed(2)}`;
      else path += ` L ${x.toFixed(2)} ${y.toFixed(2)}`;
    }
    return path;
  }, [width, height, mid, points, cycles, twoPi, t, phase, mode, amplitude]);

  const sumScaleY = mode === "sum" ? 2 : 1;

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <div className="text-lg font-medium text-gray-500">{label}</div>
        <div className="text-xs font-bold text-gray-300 uppercase tracking-widest">
          {mode === "sum" && Math.abs(phase - Math.PI) < 1e-6 ? "cancels" : mode === "sum" ? "adds" : ""}
        </div>
      </div>

      <div className="relative rounded-2xl bg-white border border-gray-100 overflow-hidden">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-[86px]"
          aria-label={label}
          role="img"
        >
          <line x1="0" y1={mid} x2={width} y2={mid} stroke="rgb(229 231 235)" strokeWidth="2" />

          <line
            x1={width * 0.72}
            y1={18}
            x2={width * 0.94}
            y2={18}
            stroke="rgb(107 114 128)"
            strokeWidth="2"
            strokeDasharray="7 6"
            opacity="0.65"
          />
          <polygon
            points={`${width * 0.94},14 ${width * 0.94},22 ${width * 0.97},18`}
            fill="rgb(107 114 128)"
            opacity="0.65"
          />

          <g transform={`scale(1 ${sumScaleY}) translate(0 ${mode === "sum" ? -(height * 0.25) : 0})`}>
            <path d={d} fill="none" stroke={color} strokeWidth="4" strokeLinecap="round" />
          </g>

          <circle cx="8" cy="10" r="3" fill="rgb(107 114 128)" opacity="0.6" />
          <circle cx="8" cy={height - 10} r="3" fill="rgb(107 114 128)" opacity="0.6" />
        </svg>
      </div>
    </div>
  );
};

/* ------------------------------ GLYPH COMPONENTS ------------------------------ */

const ComparisonCard = ({ title, traditional, glyph, labels }: any) => (
  <div className="p-10 bg-white rounded-[2.5rem] shadow-xl shadow-gray-200/50 border border-gray-100 flex flex-col justify-between">
    <div>
      <h3 className="text-xs font-bold text-gray-300 uppercase tracking-widest mb-6">{title}</h3>
      <div className="mb-8">
        <p className="text-[10px] text-gray-400 font-bold uppercase mb-2">Traditional</p>
        <p className="text-lg text-gray-600 font-light leading-snug tracking-tight">{traditional}</p>
      </div>
    </div>
    <div className="pt-8 border-t border-gray-50">
      <p className="text-[10px] text-[#0071e3] font-bold uppercase mb-4 tracking-wider">Glyph OS</p>
      <div className="text-5xl mb-3">{glyph}</div>
      <p className="text-xs font-medium text-gray-400 uppercase tracking-tighter">{labels}</p>
    </div>
  </div>
);

const GlyphTranslateDemo = () => {
  const [lang, setLang] = useState<CodeLang>("photon");
  const [source, setSource] = useState(
    [
      "# Photon test script for SCI IDE",
      "# Expect: container_id, wave, resonance, memory -> glyphs",
      "⊕ container main {",
      '  wave "hello";',
      "  resonance 0.42;",
      '  memory "sticky-notes";',
      "}",
    ].join("\n"),
  );

  const [out, setOut] = useState<string>("—");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [stats, setStats] = useState<{ before: number; after: number; pct: number } | null>(null);

  const run = async () => {
    if (!source.trim()) {
      setOut("—");
      setStats(null);
      setErr(null);
      return;
    }
    try {
      setBusy(true);
      setErr(null);

      const resp = await translateToGlyphs(source, lang);
      const translated = resp.translated ?? "";
      setOut(translated || "—");

      const before = resp.chars_before ?? source.length;
      const after = resp.chars_after ?? translated.length;
      const pct = before > 0 ? (1 - after / before) * 100 : 0;
      setStats({ before, after, pct });
    } catch (e: any) {
      setErr(e?.message || "Translate failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="w-full bg-white rounded-[2.5rem] shadow-xl shadow-gray-200/50 border border-gray-100 p-10">
      <div className="flex items-start justify-between gap-6 mb-6">
        <div>
          <div className="text-xs font-bold text-gray-300 uppercase tracking-widest">Glyph Translator</div>
          <div className="text-sm text-gray-500 mt-1">Source (.PTN) → Translated glyph stream</div>
        </div>

        <button
          onClick={run}
          disabled={busy}
          className={`px-10 py-3 rounded-full text-sm font-semibold transition-all duration-300 ${
            busy ? "bg-gray-200 text-gray-500" : "bg-[#0071e3] text-white shadow-md hover:brightness-110"
          }`}
        >
          {busy ? "Translating…" : "Translate"}
        </button>
      </div>

      {err ? <div className="text-sm text-red-600 mb-6 whitespace-pre-wrap">{err}</div> : null}

      <div className="grid md:grid-cols-2 gap-8">
        <EditorPane
          title="SOURCE (.PTN)"
          rightControl={
            <div className="flex items-center gap-3">
              <div className="text-[10px] text-gray-400 font-bold uppercase tracking-widest">CODE LANG:</div>
              <select
                value={lang}
                onChange={(e) => setLang(e.target.value as CodeLang)}
                className="px-4 py-2 rounded-xl border border-gray-200 bg-white text-sm font-semibold text-gray-700 shadow-sm outline-none focus:ring-2 focus:ring-blue-200"
              >
                <option value="photon">Photon (.ptn)</option>
                <option value="python">Python (.py)</option>
              </select>
            </div>
          }
        >
          <CodeWithLines value={source} onChange={setSource} placeholder="Type code…" />
        </EditorPane>

        <EditorPane
          title="GLYPH STREAM"
          rightControl={
            stats ? (
              <div className="text-[11px] text-gray-400">
                <span className="font-semibold">{stats.pct.toFixed(1)}%</span> shorter ({stats.before} →{" "}
                {stats.after})
              </div>
            ) : null
          }
        >
          <ReadOnlyCodeWithLines value={out} />
        </EditorPane>
      </div>
    </div>
  );
};

const EditorPane = ({
  title,
  rightControl,
  children,
}: {
  title: string;
  rightControl?: React.ReactNode;
  children: React.ReactNode;
}) => (
  <div className="rounded-[2rem] border border-gray-100 bg-white overflow-hidden shadow-sm">
    <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between gap-4">
      <div className="text-sm font-bold text-gray-700">{title}</div>
      {rightControl ? <div>{rightControl}</div> : <div />}
    </div>
    <div className="bg-[#fafafa]">{children}</div>
  </div>
);

const CodeWithLines = ({
  value,
  onChange,
  placeholder,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) => {
  const lines = useMemo(() => Math.max(1, value.split("\n").length), [value]);

  return (
    <div className="flex font-mono text-sm leading-6">
      <div className="select-none text-right text-gray-300 bg-white/40 border-r border-gray-100 px-4 py-4 min-w-[3rem]">
        {Array.from({ length: lines }, (_, i) => (
          <div key={i}>{i + 1}</div>
        ))}
      </div>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        rows={Math.max(10, lines)}
        placeholder={placeholder}
        spellCheck={false}
        className="flex-1 resize-none bg-transparent px-4 py-4 outline-none text-gray-800"
      />
    </div>
  );
};

const ReadOnlyCodeWithLines = ({ value }: { value: string }) => {
  const text = value && value.trim().length ? value : "—";
  const lines = useMemo(() => Math.max(1, text.split("\n").length), [text]);

  return (
    <div className="flex font-mono text-sm leading-6">
      <div className="select-none text-right text-gray-300 bg-white/40 border-r border-gray-100 px-4 py-4 min-w-[3rem]">
        {Array.from({ length: lines }, (_, i) => (
          <div key={i}>{i + 1}</div>
        ))}
      </div>
      <pre className="flex-1 whitespace-pre-wrap break-words px-4 py-4 text-gray-800">{text}</pre>
    </div>
  );
};

export default Home;