// frontend/pages/index.tsx
"use client";

import { useState } from "react";
import type { NextPage } from "next";

/**
 * ⚠️ NOTE: QFC is currently disabled to prevent the useQFCFocus error
 * breaking the demo until the Provider is implemented.
 */

const Home: NextPage = () => {
  const [activeTab, setActiveTab] = useState<"glyph" | "symatics">("glyph");
  const [showGlyphDemo, setShowGlyphDemo] = useState(false);

  return (
    <div className="min-h-screen bg-[#f5f5f7] text-[#1d1d1f] selection:bg-blue-100 font-sans antialiased">
      {/* ✅ LOCAL SCROLL CONTAINER (because global html/body overflow is hidden) */}
      <div className="h-screen overflow-y-auto">
        <main className="relative z-10 flex flex-col items-center justify-start min-h-full px-6 max-w-5xl mx-auto py-16 pb-32">
          {/*  Minimalist Tab Switcher (Apple Style) */}
          <nav className="mb-16 p-1 bg-white/70 backdrop-blur-md border border-gray-200 rounded-full flex gap-1 shadow-sm">
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

          {/* 📦 Content Area */}
          <div className="w-full">
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

                {/* ✅ Glyph Demo button + panel */}
                <div className="flex flex-col items-center gap-6">
                  <button
                    onClick={() => setShowGlyphDemo((v) => !v)}
                    className="px-10 py-3 rounded-full text-sm font-semibold transition-all duration-300 bg-[#0071e3] text-white shadow-md hover:brightness-110"
                  >
                    Glyph Demo
                  </button>

                  {showGlyphDemo ? <GlyphTranslateDemo /> : null}
                </div>
              </section>
            )}

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

                <div className="bg-white rounded-[3rem] p-16 text-center shadow-xl shadow-gray-200/50 border border-gray-100">
                  <div className="text-8xl mb-8 tracking-widest flex justify-center items-center gap-4">
                    〰️ <span className="text-3xl text-gray-300">+</span> 〰️{" "}
                    <span className="text-3xl text-gray-300">=</span>{" "}
                    <span className="text-[#0071e3] drop-shadow-xl font-bold">✨</span>
                  </div>

                  <p className="text-gray-400 text-lg italic">
                    〰️ + 〰️ = ✨ reads as “constructive interference produces a coherent/bright result”
                    (nice for Symatics).
                  </p>
                </div>

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

          {/* 🔘 Call to Action */}
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

      {/* 📟 Control HUD */}
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

type TranslateResponse = {
  translated?: string;
  glyph_count?: number;
  chars_before?: number;
  chars_after?: number;
  compression_ratio?: number;
};

async function translateToGlyphs(text: string): Promise<TranslateResponse> {
  const res = await fetch("/api/photon/translate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, language: "python" }),
  });
  if (!res.ok) {
    const msg = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status} — ${msg || res.statusText}`);
  }
  return (await res.json()) as TranslateResponse;
}

const GlyphTranslateDemo = () => {
  const [source, setSource] = useState(
    "Open document, scan for key points, extract data, summarize, and file.",
  );
  const [out, setOut] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [stats, setStats] = useState<{ before: number; after: number; pct: number } | null>(null);

  const run = async () => {
    if (!source.trim()) {
      setOut("");
      setStats(null);
      return;
    }
    try {
      setBusy(true);
      setErr(null);
      const resp = await translateToGlyphs(source);
      const translated = resp.translated ?? "";
      setOut(translated);

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
      <div className="flex items-center justify-between gap-4 mb-6">
        <div>
          <div className="text-xs font-bold text-gray-300 uppercase tracking-widest">Glyph Translator</div>
          <div className="text-sm text-gray-500 mt-1">Left: source · Right: translated glyph stream</div>
        </div>
        <button
          onClick={run}
          disabled={busy}
          className={`px-6 py-2.5 rounded-full text-sm font-semibold transition-all duration-300 ${
            busy ? "bg-gray-200 text-gray-500" : "bg-[#0071e3] text-white shadow-md hover:brightness-110"
          }`}
        >
          {busy ? "Translating…" : "Translate"}
        </button>
      </div>

      {err ? <div className="text-sm text-red-600 mb-4">{err}</div> : null}

      <div className="grid md:grid-cols-2 gap-8">
        <div className="rounded-2xl border border-gray-100 bg-[#fafafa] p-6">
          <div className="text-[10px] text-gray-400 font-bold uppercase mb-3">Source</div>
          <textarea
            value={source}
            onChange={(e) => setSource(e.target.value)}
            rows={10}
            className="w-full resize-none bg-transparent outline-none text-gray-700 leading-relaxed"
            placeholder="Type text…"
          />
        </div>

        <div className="rounded-2xl border border-gray-100 bg-[#fafafa] p-6">
          <div className="flex items-center justify-between mb-3">
            <div className="text-[10px] text-[#0071e3] font-bold uppercase tracking-wider">Glyph Stream</div>
            {stats ? (
              <div className="text-[11px] text-gray-400">
                <span className="font-semibold">{stats.pct.toFixed(1)}%</span> shorter ({stats.before} → {stats.after})
              </div>
            ) : null}
          </div>
          <pre className="whitespace-pre-wrap break-words text-gray-700 leading-relaxed min-h-[12rem]">
            {out || "—"}
          </pre>
        </div>
      </div>
    </div>
  );
};

export default Home;