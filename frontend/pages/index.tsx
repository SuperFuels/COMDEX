// frontend/pages/index.tsx
"use client";

import { useMemo, useRef, useState } from "react";
import type { NextPage } from "next";

/**
 * ⚠️ NOTE: QFC is currently disabled to prevent the useQFCFocus error
 * breaking the demo until the Provider is implemented.
 */

const Home: NextPage = () => {
  const [activeTab, setActiveTab] = useState<"glyph" | "symatics">("glyph");

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

                {/* ✅ Inline demo (no extra "Glyph Demo" toggle button) */}
                <GlyphTranslateDemo />
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
                    〰️ + 〰️ = ✨ reads as “constructive interference produces a coherent/bright result”.
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

async function translateToGlyphs(text: string, language: "photon" | "python"): Promise<TranslateResponse> {
  // Try POST first (ideal for larger payloads)
  let res = await fetch("/api/photon/translate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, language }),
  });

  // If the route is implemented as GET-only (common in Next route handlers), fall back.
  if (res.status === 405) {
    const url = `/api/photon/translate?text=${encodeURIComponent(text)}&language=${encodeURIComponent(language)}`;
    res = await fetch(url, { method: "GET" });
  }

  if (!res.ok) {
    const msg = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status} — ${msg || res.statusText}`);
  }

  return (await res.json()) as TranslateResponse;
}

function lineNumbersFor(text: string): string {
  const lines = Math.max(1, (text || "").split("\n").length);
  let out = "";
  for (let i = 1; i <= lines; i++) out += (i === 1 ? "" : "\n") + i;
  return out;
}

const EditorPane = ({
  title,
  rightHeader,
  value,
  onChange,
  placeholder,
  langLabel,
  langValue,
  onLangChange,
}: {
  title: string;
  rightHeader?: React.ReactNode;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  langLabel?: string;
  langValue?: string;
  onLangChange?: (v: string) => void;
}) => {
  const gutterRef = useRef<HTMLPreElement>(null);
  const areaRef = useRef<HTMLTextAreaElement>(null);

  const nums = useMemo(() => lineNumbersFor(value), [value]);

  const syncScroll = () => {
    if (!gutterRef.current || !areaRef.current) return;
    gutterRef.current.scrollTop = areaRef.current.scrollTop;
  };

  return (
    <div className="bg-white rounded-[2rem] border border-gray-200 shadow-sm overflow-hidden">
      <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
        <div className="text-sm font-semibold text-gray-700 tracking-wide">{title}</div>
        <div className="flex items-center gap-3">
          {rightHeader}
          {langLabel && onLangChange ? (
            <div className="flex items-center gap-3">
              <span className="text-xs font-bold uppercase tracking-widest text-gray-400">{langLabel}</span>
              <select
                value={langValue}
                onChange={(e) => onLangChange(e.target.value)}
                className="bg-white border border-gray-200 rounded-xl px-4 py-2 text-sm font-semibold text-gray-700 outline-none focus:ring-2 focus:ring-blue-200"
              >
                <option value="photon">Photon (.ptn)</option>
                <option value="python">Python</option>
              </select>
            </div>
          ) : null}
        </div>
      </div>

      <div className="flex bg-[#fafafa]">
        {/* gutter */}
        <pre
          ref={gutterRef}
          className="select-none w-14 shrink-0 text-right pr-4 py-5 text-sm leading-6 font-mono text-gray-300 border-r border-gray-200 overflow-hidden"
        >
          {nums}
        </pre>

        {/* editor */}
        <textarea
          ref={areaRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onScroll={syncScroll}
          spellCheck={false}
          placeholder={placeholder}
          className="w-full h-[22rem] resize-none bg-transparent px-5 py-5 text-sm leading-6 font-mono text-gray-800 outline-none"
        />
      </div>
    </div>
  );
};

const ReadonlyPane = ({ title, value }: { title: string; value: string }) => {
  const gutterRef = useRef<HTMLPreElement>(null);
  const bodyRef = useRef<HTMLPreElement>(null);

  const shown = value && value.length ? value : "—";
  const nums = useMemo(() => lineNumbersFor(shown), [shown]);

  const syncScroll = () => {
    if (!gutterRef.current || !bodyRef.current) return;
    gutterRef.current.scrollTop = bodyRef.current.scrollTop;
  };

  return (
    <div className="bg-white rounded-[2rem] border border-gray-200 shadow-sm overflow-hidden">
      <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
        <div className="text-sm font-semibold text-gray-700 tracking-wide">{title}</div>
      </div>

      <div className="flex bg-[#fafafa]">
        <pre
          ref={gutterRef}
          className="select-none w-14 shrink-0 text-right pr-4 py-5 text-sm leading-6 font-mono text-gray-300 border-r border-gray-200 overflow-hidden"
        >
          {nums}
        </pre>

        <pre
          ref={bodyRef}
          onScroll={syncScroll}
          className="w-full h-[22rem] overflow-auto px-5 py-5 text-sm leading-6 font-mono text-gray-800 whitespace-pre"
        >
          {shown}
        </pre>
      </div>
    </div>
  );
};

const GlyphTranslateDemo = () => {
  const [codeLang, setCodeLang] = useState<"photon" | "python">("photon");
  const [source, setSource] = useState(
    `# Photon test script for SCI IDE
# Expect: container_id, wave, resonance, memory -> glyphs
⊕ container main {
  wave "hello";
  resonance 0.42;
  memory "sticky-notes";
}
`,
  );
  const [out, setOut] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [stats, setStats] = useState<{ before: number; after: number; pct: number } | null>(null);

  const ext = codeLang === "photon" ? ".PTN" : "PY";

  const run = async () => {
    if (!source.trim()) {
      setOut("");
      setStats(null);
      return;
    }
    try {
      setBusy(true);
      setErr(null);

      const resp = await translateToGlyphs(source, codeLang);
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
      <div className="flex items-center justify-between gap-6 mb-6">
        <div>
          <div className="text-xs font-bold text-gray-300 uppercase tracking-widest">Glyph Translator</div>
          <div className="text-sm text-gray-500 mt-1">
            Source ({ext}) → Translated glyph stream
            {stats ? (
              <span className="ml-3 text-gray-400">
                <span className="font-semibold">{stats.pct.toFixed(1)}%</span> shorter ({stats.before} → {stats.after})
              </span>
            ) : null}
          </div>
        </div>

        <button
          onClick={run}
          disabled={busy}
          className={`px-8 py-3 rounded-full text-sm font-semibold transition-all duration-300 ${
            busy ? "bg-gray-200 text-gray-500" : "bg-[#0071e3] text-white shadow-md hover:brightness-110"
          }`}
        >
          {busy ? "Translating…" : "Translate"}
        </button>
      </div>

      {err ? <div className="text-sm text-red-600 mb-6">{err}</div> : null}

      <div className="grid md:grid-cols-2 gap-8">
        <EditorPane
          title={`SOURCE (${ext})`}
          langLabel="CODE LANG:"
          langValue={codeLang}
          onLangChange={(v) => setCodeLang(v as "photon" | "python")}
          value={source}
          onChange={setSource}
          placeholder="Type source…"
        />

        <ReadonlyPane title="GLYPH STREAM" value={out} />
      </div>
    </div>
  );
};

export default Home;