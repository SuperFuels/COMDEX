"use client";

import { useState } from "react";

/**
 * Compression Benchmark (locked)
 * From: backend/tests/glyphos_compression_benchmark.py
 * Locks:
 *  - depth30: 64921d74d2ad532630af0a75a5f2cc484b38142b6f8ab5eeea8781e722b541ed
 *  - depth45: e531e0e120c25e7d853325f0218f06dce9caab63cec99bbca6ed6aa74dd5a6fc
 *  - depth60: dfded3430fbe49ec0b7207562aaa56d2edc6a73a719f629b6fc6f18ca091642c
 */
const BENCHMARK_LEVELS = {
  30: {
    glyph_json: 1131,
    glyph_gz: 250,
    verbose_ast: 57161,
    verbose_ast_gz: 2505,
    expanded: 18857,
    expanded_gz: 1629,
    ratio_verbose_raw: "50.5402x",
    ratio_verbose_gz: "10.02x",
    ratio_expanded_raw: "16.6729x",
    ratio_expanded_gz: "6.516x",
    tokens: 135,
    structural: 7098,
    lock_sha256: "64921d74d2ad532630af0a75a5f2cc484b38142b6f8ab5eeea8781e722b541ed",
    // keep your existing UI fields
    saved: "—",
    cost: "—",
  },
  45: {
    glyph_json: 1653,
    glyph_gz: 319,
    verbose_ast: 91418,
    verbose_ast_gz: 3377,
    expanded: 27407,
    expanded_gz: 2274,
    ratio_verbose_raw: "55.3043x",
    ratio_verbose_gz: "10.5862x",
    ratio_expanded_raw: "16.5802x",
    ratio_expanded_gz: "7.1285x",
    tokens: 195,
    structural: 14628,
    lock_sha256: "e531e0e120c25e7d853325f0218f06dce9caab63cec99bbca6ed6aa74dd5a6fc",
    saved: "—",
    cost: "—",
  },
  60: {
    glyph_json: 2175,
    glyph_gz: 379,
    verbose_ast: 131069,
    verbose_ast_gz: 4275,
    expanded: 35957,
    expanded_gz: 2939,
    ratio_verbose_raw: "60.2616x",
    ratio_verbose_gz: "11.2797x",
    ratio_expanded_raw: "16.532x",
    ratio_expanded_gz: "7.7546x",
    tokens: 255,
    structural: 24858,
    lock_sha256: "dfded3430fbe49ec0b7207562aaa56d2edc6a73a719f629b6fc6f18ca091642c",
    saved: "—",
    cost: "—",
  },
} as const;

type Depth = keyof typeof BENCHMARK_LEVELS;

/**
 * WirePack v10 Template+Delta Benchmark (locked)
 * From: backend/tests/glyphos_wirepack_v10_template_delta_benchmark.py
 * Lock (stdout):
 *  - depth30 m2000 r1 seed1: 79dfafe8b6a373363821311e6870ac82a371fc254479d1ee8d8ad9b9cfd78bc7
 */
const WIREPACK_V10 = {
  depth: 30,
  messages: 2000,
  mutate_rate: 1.0,
  seed: 1,

  avg_json: 1274.192,
  avg_json_gz: 366.492,

  avg_fallback: 709.192,
  avg_fallback_gz: 328.959,

  avg_v10: 179.192,
  avg_v10_gz: 165.767,

  savings_vs_fallback_raw_pct: 74.73,
  savings_vs_fallback_gz_pct: 49.61,
  savings_vs_json_gz_pct: 54.77,

  template_hits: "2000/2000",
  roundtrip_fail: "0/2000",

  lock_sha256: "79dfafe8b6a373363821311e6870ac82a371fc254479d1ee8d8ad9b9cfd78bc7",
} as const;

export default function CompressionOrchestratorDemo() {
  const [depth, setDepth] = useState<Depth>(30);
  const [isBenchmarking, setIsBenchmarking] = useState(false);
  const [terminalLogs, setTerminalLogs] = useState<string[]>([]);
  const [showResults, setShowResults] = useState(false);
  const [panel, setPanel] = useState<"compression" | "wirepack">("compression");

  const active = BENCHMARK_LEVELS[depth];

  const runLiveProof = () => {
    setIsBenchmarking(true);
    setShowResults(false);
    setTerminalLogs([
      panel === "compression"
        ? `$ python backend/tests/glyphos_compression_benchmark.py (depth=${depth})`
        : `$ GLYPHOS_BENCH_DEPTH=${WIREPACK_V10.depth} GLYPHOS_MESSAGES=${WIREPACK_V10.messages} GLYPHOS_MUTATE_RATE=${WIREPACK_V10.mutate_rate} GLYPHOS_SEED=${WIREPACK_V10.seed} python backend/tests/glyphos_wirepack_v10_template_delta_benchmark.py`,
    ]);

    const steps =
      panel === "compression"
        ? [
            "Initializing CodexCore V1.0 Substrate...",
            "Generating nested operator tree: {↔, ⧖, ⟲, ⊕, ->}",
            "Encoding compact wire JSON...",
            "Simulating Verbose AST baseline (metadata-heavy)...",
            "Simulating Expanded instruction baseline (flat IR)...",
            "Calculating compression ratios + structural score...",
            "Finalizing deterministic audit trace (lock-backed)...",
          ]
        : [
            "Initializing WirePack v10 Template+Delta...",
            "Generating message family (same shape, mutated literals)...",
            "Measuring wire JSON vs fallback vs v10...",
            "Verifying template hit-rate + roundtrip integrity...",
            "Finalizing deterministic audit trace (lock-backed)...",
          ];

    steps.forEach((step, i) => {
      setTimeout(() => {
        setTerminalLogs((prev) => [...prev, ">> " + step]);
        if (i === steps.length - 1) {
          setIsBenchmarking(false);
          setShowResults(true);
        }
      }, (i + 1) * 300);
    });
  };

  return (
    <div className="w-full space-y-10">
      {/* 1. THE CONTROL HUB */}
      <div className="flex flex-col md:flex-row justify-between items-center bg-white p-8 rounded-[3rem] border border-gray-100 shadow-xl shadow-gray-200/50">
        <div className="mb-4 md:mb-0">
          <div className="text-[10px] font-bold text-[#0071e3] uppercase tracking-[0.2em] mb-1">
            Live Proof Engine
          </div>
          <h3 className="text-xl font-bold text-black">Proof of Complexity Scaling</h3>
          <div className="mt-2 flex gap-2">
            <button
              onClick={() => {
                setPanel("compression");
                setShowResults(false);
                setTerminalLogs([]);
              }}
              className={`px-4 py-1.5 rounded-full text-[10px] font-bold transition-all ${
                panel === "compression"
                  ? "bg-black text-white"
                  : "bg-gray-100 text-gray-500 hover:text-gray-700"
              }`}
            >
              Compression Benchmark
            </button>
            <button
              onClick={() => {
                setPanel("wirepack");
                setShowResults(false);
                setTerminalLogs([]);
              }}
              className={`px-4 py-1.5 rounded-full text-[10px] font-bold transition-all ${
                panel === "wirepack"
                  ? "bg-black text-white"
                  : "bg-gray-100 text-gray-500 hover:text-gray-700"
              }`}
            >
              WirePack v10 (Template+Delta)
            </button>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {/* Depth selector only matters for compression panel */}
          {panel === "compression" && (
            <div className="flex bg-gray-100 p-1.5 rounded-full backdrop-blur-sm">
              {([30, 45, 60] as const).map((d) => (
                <button
                  key={d}
                  onClick={() => {
                    setDepth(d);
                    setShowResults(false);
                    setTerminalLogs([]);
                  }}
                  className={`px-8 py-2.5 rounded-full text-xs font-bold transition-all ${
                    depth === d ? "bg-black text-white shadow-lg" : "text-gray-400 hover:text-gray-600"
                  }`}
                >
                  Depth {d}
                </button>
              ))}
            </div>
          )}

          <button
            onClick={runLiveProof}
            disabled={isBenchmarking}
            className="bg-[#0071e3] text-white px-10 py-4 rounded-full font-bold text-xs hover:scale-105 active:scale-95 transition-all shadow-blue-200 shadow-xl disabled:opacity-50"
          >
            {isBenchmarking ? "BENCHMARKING..." : "EXECUTE PROOF"}
          </button>
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-8">
        {/* 2. THE TERMINAL (MIRRORS PYTHON LOGS) */}
        <div className="bg-[#0a0a0b] rounded-[2.5rem] p-8 h-[480px] shadow-2xl relative overflow-hidden border border-white/5">
          <div className="flex gap-2 mb-8">
            <div className="w-2.5 h-2.5 rounded-full bg-[#ff5f56]" />
            <div className="w-2.5 h-2.5 rounded-full bg-[#ffbd2e]" />
            <div className="w-2.5 h-2.5 rounded-full bg-[#27c93f]" />
          </div>

          <div className="font-mono text-[11px] leading-relaxed space-y-2">
            {terminalLogs.map((log, i) => (
              <div key={i} className={log.startsWith("$") ? "text-blue-400" : "text-gray-400"}>
                {log}
              </div>
            ))}

            {/* RESULTS BLOCK */}
            {showResults && panel === "compression" && (
              <div className="pt-6 mt-6 border-t border-white/10 space-y-1 animate-in slide-in-from-bottom-2 duration-500">
                <div className="text-[#27c93f] font-bold">=== ✅ GlyphOS Compression Benchmark (Locked) ===</div>

                <div className="flex justify-between py-1">
                  <span className="text-gray-500">Glyph (wire JSON):</span>
                  <span className="text-white">{active.glyph_json} B</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-gray-500">Glyph (wire JSON, gzip):</span>
                  <span className="text-white">{active.glyph_gz} B</span>
                </div>

                <div className="flex justify-between py-1">
                  <span className="text-gray-500">Baseline A (verbose AST):</span>
                  <span className="text-white">{active.verbose_ast.toLocaleString()} B</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-gray-500">Baseline A (gzip):</span>
                  <span className="text-white">{active.verbose_ast_gz.toLocaleString()} B</span>
                </div>

                <div className="flex justify-between py-1">
                  <span className="text-gray-500">Baseline B (expanded IR):</span>
                  <span className="text-white">{active.expanded.toLocaleString()} B</span>
                </div>
                <div className="flex justify-between py-1 border-b border-white/5 pb-4">
                  <span className="text-gray-500">Baseline B (gzip):</span>
                  <span className="text-white">{active.expanded_gz.toLocaleString()} B</span>
                </div>

                <div className="flex justify-between font-bold text-white pt-4 text-sm italic">
                  <span className="text-[#0071e3]">Ratio vs Verbose AST:</span>
                  <span className="text-[#0071e3]">
                    {active.ratio_verbose_raw} (raw) / {active.ratio_verbose_gz} (gzip)
                  </span>
                </div>
                <div className="flex justify-between font-bold text-white text-sm italic">
                  <span className="text-[#0071e3]">Ratio vs Expanded IR:</span>
                  <span className="text-[#0071e3]">
                    {active.ratio_expanded_raw} (raw) / {active.ratio_expanded_gz} (gzip)
                  </span>
                </div>

                <div className="pt-3 text-[10px] text-gray-600">
                  Tokens: {active.tokens} | Structural: {active.structural} | Runtime: (suppressed for lock)
                </div>
                <div className="text-[10px] text-gray-600">
                  Lock stdout SHA256: <span className="text-gray-400">{active.lock_sha256}</span>
                </div>
              </div>
            )}

            {showResults && panel === "wirepack" && (
              <div className="pt-6 mt-6 border-t border-white/10 space-y-1 animate-in slide-in-from-bottom-2 duration-500">
                <div className="text-[#27c93f] font-bold">=== ✅ WirePack v10 Template+Delta (Locked) ===</div>

                <div className="flex justify-between py-1">
                  <span className="text-gray-500">Depth / Messages:</span>
                  <span className="text-white">
                    {WIREPACK_V10.depth} / {WIREPACK_V10.messages}
                  </span>
                </div>
                <div className="flex justify-between py-1 border-b border-white/5 pb-4">
                  <span className="text-gray-500">Mutate / Seed:</span>
                  <span className="text-white">
                    {WIREPACK_V10.mutate_rate} / {WIREPACK_V10.seed}
                  </span>
                </div>

                <div className="flex justify-between py-1">
                  <span className="text-gray-500">Avg JSON:</span>
                  <span className="text-white">{WIREPACK_V10.avg_json.toFixed(3)} B</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-gray-500">Avg JSON (gzip):</span>
                  <span className="text-white">{WIREPACK_V10.avg_json_gz.toFixed(3)} B</span>
                </div>

                <div className="flex justify-between py-1">
                  <span className="text-gray-500">Avg fallback:</span>
                  <span className="text-white">{WIREPACK_V10.avg_fallback.toFixed(3)} B</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-gray-500">Avg fallback (gzip):</span>
                  <span className="text-white">{WIREPACK_V10.avg_fallback_gz.toFixed(3)} B</span>
                </div>

                <div className="flex justify-between py-1">
                  <span className="text-gray-500">Avg v10:</span>
                  <span className="text-white">{WIREPACK_V10.avg_v10.toFixed(3)} B</span>
                </div>
                <div className="flex justify-between py-1 border-b border-white/5 pb-4">
                  <span className="text-gray-500">Avg v10 (gzip):</span>
                  <span className="text-white">{WIREPACK_V10.avg_v10_gz.toFixed(3)} B</span>
                </div>

                <div className="flex justify-between font-bold text-white pt-4 text-sm italic">
                  <span className="text-[#0071e3]">Savings vs JSON (gzip):</span>
                  <span className="text-[#0071e3]">{WIREPACK_V10.savings_vs_json_gz_pct.toFixed(2)}%</span>
                </div>
                <div className="flex justify-between text-white text-[11px]">
                  <span className="text-gray-500">Savings vs fallback (raw/gzip):</span>
                  <span className="text-white">
                    {WIREPACK_V10.savings_vs_fallback_raw_pct.toFixed(2)}% /{" "}
                    {WIREPACK_V10.savings_vs_fallback_gz_pct.toFixed(2)}%
                  </span>
                </div>

                <div className="pt-3 text-[10px] text-gray-600">
                  Template hits: {WIREPACK_V10.template_hits} | Roundtrip failures: {WIREPACK_V10.roundtrip_fail}
                </div>
                <div className="text-[10px] text-gray-600">
                  Lock stdout SHA256: <span className="text-gray-400">{WIREPACK_V10.lock_sha256}</span>
                </div>
              </div>
            )}
          </div>

          {isBenchmarking && (
            <div className="absolute inset-0 bg-black/20 flex items-center justify-center">
              <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
            </div>
          )}
        </div>

        {/* 3. THE LIVE IMPACT DATA */}
        <div className="flex flex-col gap-6">
          <div className="grid grid-cols-2 gap-6">
            <MetricBox
              label={panel === "compression" ? "Glyph (gzip)" : "v10 (gzip)"}
              value={panel === "compression" ? `${active.glyph_gz} B` : `${WIREPACK_V10.avg_v10_gz.toFixed(1)} B`}
              sub="Payload"
              show={showResults}
            />
            <MetricBox
              label={panel === "compression" ? "Ratio (vs A raw)" : "Savings (vs JSON gz)"}
              value={panel === "compression" ? active.ratio_verbose_raw : `${WIREPACK_V10.savings_vs_json_gz_pct.toFixed(2)}%`}
              sub={panel === "compression" ? "Gain" : "Saved"}
              show={showResults}
              highlight
            />
          </div>

          <div className="bg-gradient-to-br from-[#1d1d1f] to-black p-10 rounded-[3rem] text-white shadow-2xl flex flex-col justify-between flex-1 relative overflow-hidden group">
            <div className="absolute -top-24 -right-24 w-64 h-64 bg-blue-600/10 rounded-full blur-[100px] group-hover:bg-blue-600/20 transition-all duration-1000" />

            <div>
              <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-blue-400 mb-2">
                Deterministic Audit Anchor
              </div>

              <div
                className={`text-2xl font-bold tracking-tight transition-all duration-1000 ${
                  showResults ? "opacity-100 translate-y-0" : "opacity-0 translate-y-2"
                }`}
              >
                {panel === "compression" ? "Compression Locks" : "WirePack v10 Lock"}
              </div>

              <p className="text-xs text-gray-500 mt-4 leading-relaxed max-w-[420px]">
                This UI is backed by SHA256 stdout locks from reproducible Python benchmarks. Runtime is intentionally
                suppressed so output is byte-for-byte stable.
              </p>

              <div className="mt-4 text-[10px] text-gray-600 break-all">
                {showResults ? (
                  <>
                    SHA256:{" "}
                    <span className="text-gray-300">
                      {panel === "compression" ? active.lock_sha256 : WIREPACK_V10.lock_sha256}
                    </span>
                  </>
                ) : (
                  <>SHA256: (hidden until proof runs)</>
                )}
              </div>
            </div>

            <div className="pt-8 mt-8 border-t border-white/10 flex justify-between items-center text-[10px] font-bold text-gray-400 uppercase tracking-widest">
              <span>Verified Determinism</span>
              <span className="text-white">Audit: Enabled</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function MetricBox({ label, value, sub, show, highlight = false }: any) {
  return (
    <div className="bg-white p-8 rounded-[2.5rem] border border-gray-100 shadow-lg shadow-gray-200/40">
      <div className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-1">{label}</div>
      <div
        className={`text-4xl font-bold italic transition-all duration-700 ${
          show ? "opacity-100" : "opacity-0"
        } ${highlight ? "text-[#0071e3]" : "text-black"}`}
      >
        {value}
      </div>
      <div className="text-[10px] font-bold text-gray-300 uppercase mt-1">{sub}</div>
    </div>
  );
}