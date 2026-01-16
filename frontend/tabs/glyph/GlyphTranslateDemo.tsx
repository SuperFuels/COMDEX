// frontend/tabs/glyph/GlyphTranslateDemo.tsx
"use client";

import React, { useMemo, useState } from "react";

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

// ✅ Build URL robustly (avoids double slashes)
function apiUrl(path: string) {
  if (!path.startsWith("/")) path = `/${path}`;
  return API_BASE ? `${API_BASE}${path}` : path;
}

async function translateToGlyphs(code: string, lang: CodeLang): Promise<TranslateResponse> {
  // POST /api/photon/translate  body: { text, language }
  const res = await fetch(apiUrl("/api/photon/translate"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: code, language: lang }),
  });

  if (!res.ok) {
    const ct = res.headers.get("content-type") || "";
    const raw = await res.text().catch(() => "");

    const hint = ct.includes("text/html")
      ? "HTML response — likely not hitting FastAPI. Check next.config.js rewrites for /api/:path* and NEXT_PUBLIC_API_URL."
      : "";

    const msg = (raw && raw.slice(0, 400)) || res.statusText;
    throw new Error(`HTTP ${res.status} — ${msg}${hint ? `\n${hint}` : ""}`);
  }

  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return (await res.json()) as TranslateResponse;

  const text = await res.text();
  return { translated: text, chars_before: code.length, chars_after: text.length };
}

export default function GlyphTranslateDemo() {
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
                <span className="font-semibold">{stats.pct.toFixed(1)}%</span> shorter ({stats.before} → {stats.after})
              </div>
            ) : null
          }
        >
          <ReadOnlyCodeWithLines value={out} />
        </EditorPane>
      </div>
    </div>
  );
}

function EditorPane({
  title,
  rightControl,
  children,
}: {
  title: string;
  rightControl?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-[2rem] border border-gray-100 bg-white overflow-hidden shadow-sm">
      <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between gap-4">
        <div className="text-sm font-bold text-gray-700">{title}</div>
        {rightControl ? <div>{rightControl}</div> : <div />}
      </div>
      <div className="bg-[#fafafa]">{children}</div>
    </div>
  );
}

function CodeWithLines({
  value,
  onChange,
  placeholder,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
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
}

function ReadOnlyCodeWithLines({ value }: { value: string }) {
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
}