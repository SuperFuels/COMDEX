"use client";

import { useEffect, useMemo, useState } from "react";

export type CodeLang = "photon" | "python";

export type TranslateResponse = {
  translated?: string;
  glyph_count?: number;
  chars_before?: number;
  chars_after?: number;
  compression_ratio?: number;
};

const DEFAULT_SOURCE = [
  "# Photon test script for SCI IDE",
  "# Expect: container_id, wave, resonance, memory ->",
  "# glyphs",
  "@ container main {",
  '  wave "hello";',
  "  resonance 0.42;",
  '  memory "sticky-notes";',
  "}",
].join("\n");

const API_BASE =
  (typeof window !== "undefined" &&
    (process.env.NEXT_PUBLIC_API_URL || "")
      .replace(/\/+$/, "")
      .replace(/\/api\/?$/, "")) ||
  "";

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
    const raw = await res.text().catch(() => "");
    const msg = (raw && raw.slice(0, 400)) || res.statusText;
    throw new Error(`HTTP ${res.status} — ${msg}`);
  }

  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return (await res.json()) as TranslateResponse;

  const text = await res.text();
  return { translated: text, chars_before: code.length, chars_after: text.length };
}

function CodeLines({
  value,
  onChange,
  readOnly,
  minRows = 12,
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

function PanelShell({
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
        <div className="text-xs font-bold tracking-widest uppercase text-gray-400">{title}</div>
        {right ? <div>{right}</div> : null}
      </div>
      <div className="bg-[#fafafa]">{children}</div>
    </div>
  );
}

export default function PhotonTranslatorWidget({
  source,
  onSourceChange,
  lang,
  onLangChange,
  translated,
  onTranslatedChange,
  initialSource = DEFAULT_SOURCE,
  initialLang = "photon",
  title = "GLYPH TRANSLATOR",
  subtitle = "Source (.PTN) → Translated glyph stream",
  className = "",
}: {
  // controlled (optional)
  source?: string;
  onSourceChange?: (v: string) => void;
  lang?: CodeLang;
  onLangChange?: (v: CodeLang) => void;
  translated?: string;
  onTranslatedChange?: (v: string) => void;

  // uncontrolled defaults
  initialSource?: string;
  initialLang?: CodeLang;

  // copy
  title?: string;
  subtitle?: string;

  className?: string;
}) {
  const [localSource, setLocalSource] = useState(initialSource);
  const [localLang, setLocalLang] = useState<CodeLang>(initialLang);
  const [localOut, setLocalOut] = useState("—");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const src = source ?? localSource;
  const out = translated ?? localOut;
  const L = lang ?? localLang;

  // if parent swaps scenarios, they’ll pass new `source`; keep output sane:
  useEffect(() => {
    if (translated === undefined) setLocalOut("—");
    setErr(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [source]);

  const setSrc = (v: string) => {
    onSourceChange?.(v);
    if (source === undefined) setLocalSource(v);
  };

  const setLang2 = (v: CodeLang) => {
    onLangChange?.(v);
    if (lang === undefined) setLocalLang(v);
  };

  const setOut = (v: string) => {
    onTranslatedChange?.(v);
    if (translated === undefined) setLocalOut(v);
  };

  const doTranslate = async () => {
    try {
      setBusy(true);
      setErr(null);
      const resp = await translateToGlyphs(src, L);
      const wire = (resp.translated ?? "").trim() || "—";
      setOut(wire);
    } catch (e: any) {
      setErr(e?.message || "Translate failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={`w-full bg-white rounded-[3rem] shadow-2xl shadow-gray-200/60 border border-gray-100 p-10 md:p-12 ${className}`}>
      <div className="flex items-start justify-between gap-6">
        <div>
          <div className="text-xs font-bold text-gray-300 uppercase tracking-widest">{title}</div>
          <div className="text-sm text-gray-400 mt-2">{subtitle}</div>
        </div>

        <button
          type="button"
          onClick={doTranslate}
          disabled={busy}
          className={`px-10 py-3 rounded-full text-sm font-semibold transition-all ${
            busy ? "bg-gray-200 text-gray-500" : "bg-[#0071e3] text-white shadow-md hover:brightness-110"
          }`}
        >
          {busy ? "Translating…" : "Translate"}
        </button>
      </div>

      {err ? (
        <div className="mt-6 text-sm text-red-600 whitespace-pre-wrap">{err}</div>
      ) : null}

      <div className="mt-10 grid lg:grid-cols-2 gap-8">
        <PanelShell
          title="SOURCE (.PTN)"
          right={
            <div className="flex items-center gap-3">
              <div className="text-[10px] font-bold uppercase tracking-widest text-gray-300">CODE LANG:</div>
              <select
                value={L}
                onChange={(e) => setLang2(e.target.value as CodeLang)}
                className="px-4 py-2 rounded-full border border-gray-200 bg-white text-xs font-bold text-gray-700 shadow-sm outline-none"
              >
                <option value="photon">Photon (.ptn)</option>
                <option value="python">Python (.py)</option>
              </select>
            </div>
          }
        >
          <div className="rounded-[2rem] border border-gray-100 bg-white overflow-hidden">
            <CodeLines value={src} onChange={setSrc} minRows={14} />
          </div>
        </PanelShell>

        <PanelShell title="GLYPH STREAM">
          <div className="rounded-[2rem] border border-gray-100 bg-white overflow-hidden">
            <CodeLines value={out} readOnly minRows={14} />
          </div>
        </PanelShell>
      </div>
    </div>
  );
}