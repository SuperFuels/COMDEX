// frontend/pages/index.tsx
"use client";

import { useMemo, useState } from "react";
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

async function translateToGlyphs(code: string, lang: CodeLang): Promise<TranslateResponse> {
  const res = await fetch("/api/photon/translate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      code, // fallback key
      text: code, // compatibility key
      source: code, // compatibility key
      lang, // fallback key
      language: lang, // compatibility key
    }),
  });

  if (!res.ok) {
    const ct = res.headers.get("content-type") || "";
    const raw = await res.text().catch(() => "");
    const msg = ct.includes("text/html")
      ? `${res.status} ${res.statusText} (HTML response — route missing or wrong method)`
      : raw.slice(0, 300) || res.statusText;
    throw new Error(`HTTP ${res.status} — ${msg}`);
  }

  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return (await res.json()) as TranslateResponse;

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

                {/* ✅ Translator panel under the quote */}
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

                {/* Core equation hero */}
                <div className="bg-white rounded-[3rem] p-16 text-center shadow-xl shadow-gray-200/50 border border-gray-100">
                  <div className="text-8xl mb-8 tracking-widest flex justify-center items-center gap-4">
                    〰️ <span className="text-3xl text-gray-300">+</span> 〰️{" "}
                    <span className="text-3xl text-gray-300">=</span>{" "}
                    <span className="text-[#0071e3] drop-shadow-xl font-bold">✨</span>
                  </div>
                  <p className="text-gray-400 text-lg italic">
                    “Constructive interference produces a coherent/bright result.”
                  </p>
                </div>

                {/* ✅ NEW: Symatics demo */}
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
          </div>

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
  const [waveA, setWaveA] = useState(50);
  const [waveB, setWaveB] = useState(50);

  // When waves are aligned, coherence is high
  const resonance = useMemo(() => {
    const diff = Math.abs(waveA - waveB);
    return Math.max(0, 100 - diff);
  }, [waveA, waveB]);

  return (
    <div className="w-full bg-white rounded-[2.5rem] shadow-xl border border-gray-100 p-10 space-y-10">
      <div className="flex justify-between items-end">
        <div>
          <div className="text-xs font-bold text-gray-300 uppercase tracking-widest">
            Resonance Workbench
          </div>
          <h3 className="text-xl font-semibold text-gray-800 mt-1">Adjust Pattern Alignment</h3>
        </div>
        <div className="text-right">
          <span className="text-xs font-bold text-gray-400 uppercase block">Coherence Level</span>
          <span
            className={`text-3xl font-mono font-bold ${
              resonance > 90 ? "text-blue-500" : "text-gray-700"
            }`}
          >
            {resonance}% {resonance > 90 && "✨"}
          </span>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-12">
        {/* Controls */}
        <div className="space-y-8">
          <div className="space-y-4">
            <label className="flex justify-between text-sm font-medium text-gray-500">
              <span>Intent Wave (A)</span>
              <span className="font-mono italic">〰️ {waveA}Hz</span>
            </label>
            <input
              type="range"
              min="0"
              max="100"
              value={waveA}
              onChange={(e) => setWaveA(parseInt(e.target.value))}
              className="w-full h-1.5 bg-gray-100 rounded-lg appearance-none cursor-pointer accent-blue-600"
            />
          </div>

          <div className="space-y-4">
            <label className="flex justify-between text-sm font-medium text-gray-500">
              <span>System Wave (B)</span>
              <span className="font-mono italic">〰️ {waveB}Hz</span>
            </label>
            <input
              type="range"
              min="0"
              max="100"
              value={waveB}
              onChange={(e) => setWaveB(parseInt(e.target.value))}
              className="w-full h-1.5 bg-gray-100 rounded-lg appearance-none cursor-pointer accent-blue-600"
            />
          </div>
        </div>

        {/* Output */}
        <div className="flex flex-col items-center justify-center bg-[#fafafa] rounded-3xl p-8 border border-dashed border-gray-200">
          <div className="text-sm text-gray-400 uppercase font-bold tracking-tighter mb-4">
            Symatic Output
          </div>

          <div
            className="transition-all duration-500 ease-out flex items-center justify-center"
            style={{
              transform: `scale(${0.5 + resonance / 100})`,
              filter: `blur(${Math.max(0, (100 - resonance) / 10)}px)`,
              opacity: 0.2 + resonance / 100,
            }}
          >
            <span className="text-9xl">✨</span>
          </div>

          <p className="mt-6 text-xs text-center text-gray-400 max-w-[220px]">
            {resonance > 90
              ? "Pattern locked. Resonance achieved. Trigger ready."
              : "Adjust sliders to align wave patterns."}
          </p>
        </div>
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