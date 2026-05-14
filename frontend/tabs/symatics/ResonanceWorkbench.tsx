"use client";

import { useEffect, useMemo, useRef, useState } from "react";

export default function ResonanceWorkbench() {
  const [paused, setPaused] = useState(false);
  const [amplitude, setAmplitude] = useState(18);
  const [cycles, setCycles] = useState(6);
  const [speed, setSpeed] = useState(1);

  const [t, setT] = useState(0);
  const rafRef = useRef<number | null>(null);
  const lastRef = useRef<number>(0);

  useEffect(() => {
    if (paused) return;

    const loop = (now: number) => {
      const last = lastRef.current || now;
      const dt = (now - last) / 1000;
      lastRef.current = now;
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
          <div className="text-xs font-bold text-gray-300 uppercase tracking-widest">Wave Interference</div>
          <h3 className="text-xl font-semibold text-gray-800 mt-1">
            Constructive vs Destructive (A, B, and A+B)
          </h3>
          <p className="text-sm text-gray-500 mt-2">
            Toggle motion, then adjust amplitude / frequency to see how superposition changes the combined result.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setPaused((p) => !p)}
            className={`px-5 py-2 rounded-full text-sm font-semibold transition-all ${
              paused ? "bg-[#0071e3] text-white shadow-md hover:brightness-110" : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            }`}
          >
            {paused ? "Play" : "Pause"}
          </button>
          <div className="text-xs text-gray-400 font-bold uppercase tracking-widest">{paused ? "stopped" : "running"}</div>
        </div>
      </div>

      <div className="grid md:grid-cols-3 gap-6">
        <Slider label="Amplitude" value={amplitude} min={8} max={28} step={1} onChange={setAmplitude} suffix="px" />
        <Slider label="Frequency" value={cycles} min={3} max={9} step={1} onChange={setCycles} suffix="cycles" />
        <Slider label="Speed" value={speed} min={0} max={3} step={0.1} onChange={setSpeed} suffix="×" />
      </div>

      <div className="grid md:grid-cols-2 gap-10">
        <WavePanel title="constructive interference" t={t} amplitude={amplitude} cycles={cycles} phaseB={0} />
        <WavePanel title="destructive interference" t={t} amplitude={amplitude} cycles={cycles} phaseB={Math.PI} />
      </div>
    </div>
  );
}

function Slider({
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
}) {
  return (
    <div className="space-y-3">
      <label className="flex justify-between text-sm font-medium text-gray-500">
        <span>{label}</span>
        <span className="font-mono italic">
          {value.toFixed(step < 1 ? 1 : 0)}
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
}

function WavePanel({
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
}) {
  return (
    <div className="bg-[#fafafa] rounded-3xl p-8 border border-gray-100">
      <div className="text-2xl md:text-3xl font-semibold text-gray-700 tracking-tight mb-8">{title}</div>
      <div className="space-y-8">
        <WaveRow label="wave A" color="rgb(185 28 28)" t={t} amplitude={amplitude} cycles={cycles} phase={0} mode="a" />
        <WaveRow label="wave B" color="rgb(13 148 136)" t={t} amplitude={amplitude} cycles={cycles} phase={phaseB} mode="b" />
        <WaveRow label="wave A+B" color="rgb(124 58 237)" t={t} amplitude={amplitude} cycles={cycles} phase={phaseB} mode="sum" />
      </div>
    </div>
  );
}

function WaveRow({
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
  mode: "a" | "b" | "sum";
}) {
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

      const v = mode === "sum" ? a + b : mode === "a" ? a : b;
      const y = mid - v * amplitude;

      if (i === 0) path += `M ${x.toFixed(2)} ${y.toFixed(2)}`;
      else path += ` L ${x.toFixed(2)} ${y.toFixed(2)}`;
    }
    return path;
  }, [cycles, twoPi, t, phase, mode, amplitude, mid]);

  const isCancel = mode === "sum" && Math.abs(phase - Math.PI) < 1e-6;

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <div className="text-lg font-medium text-gray-500">{label}</div>
        <div className="text-xs font-bold text-gray-300 uppercase tracking-widest">
          {mode === "sum" ? (isCancel ? "cancels" : "adds") : ""}
        </div>
      </div>

      <div className="relative rounded-2xl bg-white border border-gray-100 overflow-hidden">
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-[86px]" aria-label={label} role="img">
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

          <path d={d} fill="none" stroke={color} strokeWidth="4" strokeLinecap="round" />

          <circle cx="8" cy="10" r="3" fill="rgb(107 114 128)" opacity="0.6" />
          <circle cx="8" cy={height - 10} r="3" fill="rgb(107 114 128)" opacity="0.6" />
        </svg>
      </div>
    </div>
  );
}