"use client";

import Head from "next/head";
import { useEffect, useRef, useState } from "react";
import Shell from "@/components/Shell";

type DemoMessage = { role: "customer" | "agent"; text: string };
type NetworkMode = "standby" | "searching" | "complete";

const conversation: DemoMessage[] = [
  { role: "customer", text: "I need a plumber. My kitchen tap is leaking." },
  { role: "agent", text: "I can take that to the market. Where does the work need to happen?" },
  { role: "customer", text: "Kensington, London." },
  { role: "agent", text: "When do you need the plumber?" },
  { role: "customer", text: "Today, as soon as possible." },
  { role: "agent", text: "That is enough to search. I’m asking suitable, available plumbing agents for their best rate and arrival time." },
];

const exampleBids = [
  { name: "Kensington Plumbing Co.", price: "£88 / hour", available: "75 minutes", terms: "Call-out included", evidence: "4.8 example rating · insured" },
  { name: "BlueLine Emergency Plumbing", price: "£95 / hour", available: "45 minutes", terms: "First hour minimum", evidence: "4.9 example rating · 126 jobs" },
  { name: "RapidFix London", price: "£108 / hour", available: "25 minutes", terms: "Urgent response rate", evidence: "4.7 example rating · insured" },
];

function NeuralMarket({ mode }: { mode: NetworkMode }) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const host = canvas?.parentElement;
    const context = canvas?.getContext("2d");
    if (!canvas || !host || !context) return;

    let width = 0;
    let height = 0;
    let frame = 0;
    let started = performance.now();
    const layerSizes = [16, 12, 8, 5, 2];
    let layers: Array<Array<{ x: number; y: number; layer: number }>> = [];
    let edges: Array<{ from: { x: number; y: number; layer: number }; to: { x: number; y: number; layer: number }; weight: number }> = [];

    const build = () => {
      const box = host.getBoundingClientRect();
      const density = Math.min(window.devicePixelRatio || 1, 2);
      width = Math.max(260, box.width);
      height = Math.max(390, box.height);
      canvas.width = Math.round(width * density);
      canvas.height = Math.round(height * density);
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      context.setTransform(density, 0, 0, density, 0, 0);
      const positions = [.055, .31, .57, .79, .945];
      layers = layerSizes.map((count, layer) => Array.from({ length: count }, (_, index) => ({
        x: width * positions[layer],
        y: 42 + (height - 92) * (index + .5) / count,
        layer,
      })));
      edges = [];
      for (let layer = 0; layer < layers.length - 1; layer += 1) {
        layers[layer].forEach((from, fromIndex) => layers[layer + 1].forEach((to, toIndex) => {
          const dense = layer === 0 || layer === layers.length - 2;
          if (dense || (fromIndex * 7 + toIndex * 11 + layer) % 3 !== 0) {
            edges.push({ from, to, weight: .18 + ((fromIndex * 13 + toIndex * 17 + layer * 5) % 70) / 100 });
          }
        }));
      }
    };

    const draw = (now: number) => {
      context.clearRect(0, 0, width, height);
      edges.forEach(edge => {
        context.beginPath();
        context.moveTo(edge.from.x, edge.from.y);
        context.lineTo(edge.to.x, edge.to.y);
        context.strokeStyle = `rgba(23,72,229,${.055 + edge.weight * .1})`;
        context.lineWidth = .55 + edge.weight * .35;
        context.stroke();
      });

      const duration = mode === "searching" ? 1450 : mode === "complete" ? 2450 : 3900;
      const cycle = ((now - started) % duration) / duration;
      const wave = Math.min(layers.length - 1, cycle / .87 * (layers.length - 1));
      const current = Math.min(layers.length - 2, Math.floor(wave));
      const progress = Math.max(0, Math.min(1, wave - current));
      edges.filter(edge => edge.from.layer === current).forEach(edge => {
        const endX = edge.from.x + (edge.to.x - edge.from.x) * progress;
        const endY = edge.from.y + (edge.to.y - edge.from.y) * progress;
        const gradient = context.createLinearGradient(edge.from.x, edge.from.y, endX, endY);
        gradient.addColorStop(0, "rgba(23,72,229,.28)");
        gradient.addColorStop(.72, "rgba(23,72,229,.68)");
        gradient.addColorStop(1, "rgba(23,72,229,.98)");
        context.beginPath();
        context.moveTo(edge.from.x, edge.from.y);
        context.lineTo(endX, endY);
        context.strokeStyle = gradient;
        context.lineWidth = .8 + edge.weight * .85;
        context.stroke();
      });

      layers.forEach((layer, layerIndex) => {
        const distance = Math.abs(layerIndex - wave);
        const strength = distance < .62 ? 1 - distance / .62 : 0;
        layer.forEach(node => {
          context.beginPath();
          context.arc(node.x, node.y, strength ? 4.8 + strength * 1.3 : 3.5, 0, Math.PI * 2);
          context.fillStyle = "#111315";
          context.strokeStyle = strength ? "#1748e5" : "#111315";
          context.lineWidth = strength ? 2 : 1;
          context.shadowBlur = strength ? 8 + strength * 13 : 0;
          context.shadowColor = "#1748e5";
          context.fill();
          context.stroke();
          context.shadowBlur = 0;
        });
      });
      frame = requestAnimationFrame(draw);
    };

    build();
    started = performance.now();
    const observer = new ResizeObserver(build);
    observer.observe(host);
    frame = requestAnimationFrame(draw);
    return () => { observer.disconnect(); cancelAnimationFrame(frame); };
  }, [mode]);

  return <canvas ref={canvasRef} className="absolute inset-0 h-full w-full" aria-label="Example neural-market signals moving from request to bids" />;
}

export default function MarketPage() {
  const [visibleMessages, setVisibleMessages] = useState(0);
  const [mode, setMode] = useState<NetworkMode>("standby");
  const [showBids, setShowBids] = useState(false);
  const [selectedBid, setSelectedBid] = useState<number | null>(null);
  const [run, setRun] = useState(0);

  useEffect(() => {
    setVisibleMessages(0);
    setMode("standby");
    setShowBids(false);
    setSelectedBid(null);
    const timers = [500, 1400, 2250, 3100, 3850, 4650].map((delay, index) =>
      window.setTimeout(() => setVisibleMessages(index + 1), delay)
    );
    timers.push(window.setTimeout(() => setMode("searching"), 4650));
    timers.push(window.setTimeout(() => { setMode("complete"); setShowBids(true); }, 7000));
    return () => timers.forEach(timer => window.clearTimeout(timer));
  }, [run]);

  const serviceKnown = visibleMessages >= 1;
  const locationKnown = visibleMessages >= 3;
  const timingKnown = visibleMessages >= 5;

  return (
    <>
      <Head>
        <title>Market — Tessaris</title>
        <meta name="description" content="See how a Tessaris agent clarifies a request, asks suitable businesses and compares example bids." />
      </Head>
      <Shell activeKey="market" maxWidth="max-w-none" className="!bg-white !text-[#111315]">
        <section className="min-h-[calc(100vh-112px)] bg-white font-sans">
          <header className="flex min-h-[82px] flex-wrap items-center justify-between gap-5 px-4 py-4 sm:px-8 lg:px-12">
            <div className="flex min-w-0 flex-wrap items-center gap-x-6 gap-y-2">
              <div className="flex items-center gap-2 whitespace-nowrap text-xs font-extrabold uppercase tracking-[0.12em]"><span className="h-2 w-2 rounded-full bg-[#1748e5] shadow-[0_0_0_5px_rgba(23,72,229,0.09)]" />Agent market demonstration</div>
              <p className="max-w-3xl text-sm leading-6 text-slate-500">Watch a customer agent clarify a service request, ask suitable business agents and compare example bids.</p>
            </div>
            <div className="flex items-center gap-3 text-xs text-slate-500"><span className="bg-[#edf1ff] px-2 py-1 text-[9px] font-extrabold uppercase tracking-[0.13em] text-[#1748e5]">Illustrative demo</span><span>No real request, booking or purchase</span></div>
          </header>

          <div className="grid min-h-[calc(100vh-194px)] grid-cols-1 xl:grid-cols-[1.16fr_.72fr_1.3fr]">
            <section className="flex min-w-0 flex-col px-5 py-7 lg:px-8">
              <div className="mb-5 text-[10px] font-extrabold uppercase tracking-[0.17em] text-slate-500">01 · The ask</div>
              <div className="min-h-[330px] flex-1 overflow-y-auto pb-3" aria-live="polite">
                {conversation.slice(0, visibleMessages).map((message, index) => (
                  <div key={`${run}-${index}`} className={`mb-3 flex ${message.role === "customer" ? "justify-end" : "justify-start"}`}>
                    <div className={`max-w-[88%] px-4 py-3 text-sm leading-6 ${message.role === "customer" ? "bg-[#111315] text-white" : "bg-[#f5f5f3] text-[#111315]"}`}>
                      <span className={`mb-1 block text-[8px] font-extrabold uppercase tracking-[0.14em] ${message.role === "customer" ? "text-slate-300" : "text-slate-500"}`}>{message.role === "customer" ? "You" : "Tessaris service agent"}</span>
                      {message.text}
                    </div>
                  </div>
                ))}
              </div>
              <div className="border-t border-slate-200 pt-4">
                <div className="mb-3 flex items-center justify-between"><strong className="text-sm">Example agent job brief</strong><span className="text-[9px] font-extrabold uppercase tracking-[0.13em] text-[#1748e5]">{mode === "standby" ? "Demo conversation" : "Example request ready"}</span></div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <Brief label="Service" value={serviceKnown ? "Plumber" : "Establishing…"} />
                  <Brief label="Where" value={locationKnown ? "Kensington, London" : "Establishing…"} />
                  <Brief label="What is needed" value={serviceKnown ? "Repair a leaking kitchen tap" : "Establishing…"} wide />
                  <Brief label="When" value={timingKnown ? "Today · as soon as possible" : "Establishing…"} />
                  <Brief label="Customer" value="Signed-in app user" />
                </div>
                <button type="button" onClick={() => setRun(value => value + 1)} className="mt-3 h-11 w-full border border-slate-300 bg-white text-xs font-extrabold hover:border-slate-500">Replay demonstration</button>
              </div>
            </section>

            <section className="flex min-h-[620px] min-w-0 flex-col px-5 py-7 lg:px-7">
              <div className="mb-5 text-[10px] font-extrabold uppercase tracking-[0.17em] text-slate-500">02 · Neural market</div>
              <div className="relative min-h-[420px] flex-1 overflow-hidden">
                <NeuralMarket mode={mode} />
                <div className="absolute left-1/2 top-2 -translate-x-1/2 rounded-full border border-slate-400 bg-white/95 px-3 py-1 text-[8px] font-extrabold uppercase tracking-[0.14em]">T Neural market <span className="ml-2 text-slate-500">{mode === "complete" ? "3 bids" : mode}</span></div>
                <div className="absolute inset-x-3 bottom-2 flex justify-between text-[8px] font-bold uppercase tracking-[0.14em] text-slate-400"><span>Request</span><strong className="text-[#1748e5]">{mode === "complete" ? "Market response complete" : mode === "searching" ? "Matching · asking · ranking" : "Market standby"}</strong><span>Bids</span></div>
              </div>
              <div className="border-t border-slate-200 pt-4 text-xs">
                <MarketStep active={mode === "standby"} done={mode !== "standby"} label="Ready" text="Read the example request and authority" />
                <MarketStep active={mode === "searching"} done={mode === "complete"} label="Match" text="Match capability, location and timing" />
                <MarketStep active={mode === "searching"} done={mode === "complete"} label="Verify" text="Simulate signed requests to suitable agents" />
                <MarketStep active={mode === "complete"} done={false} label="Rank" text={mode === "complete" ? "Comparison complete · 3 fictional bids" : "Compare example bids and evidence"} />
              </div>
            </section>

            <section className="min-w-0 px-5 py-7 lg:px-8">
              <div className="mb-5 flex items-center justify-between gap-3 text-[10px] font-extrabold uppercase tracking-[0.17em] text-slate-500"><span>03 · Example bids</span><span className="bg-[#111315] px-2 py-1 text-white">{showBids ? "3 example offers" : "0 offers"}</span></div>
              <div className="grid gap-3">
                {showBids ? exampleBids.map((bid, index) => (
                  <article key={bid.name} className="border border-slate-300 bg-white p-4">
                    <div className="flex items-start justify-between gap-4"><div><p className="text-[9px] font-bold uppercase tracking-[0.13em] text-slate-500">Example bid {String(index + 1).padStart(2, "0")} · suitable for leaking taps</p><h2 className="mt-1 text-lg font-black">{bid.name}</h2><p className="mt-1 text-xs text-slate-500">Fictional demonstration business</p></div><div className="whitespace-nowrap text-right"><strong className="block text-xl">{bid.price}</strong><span className="text-[8px] font-bold uppercase tracking-[0.1em] text-[#1748e5]">Illustrative only</span></div></div>
                    <div className="mt-4 grid grid-cols-3 gap-3 border-t border-slate-200 pt-3"><Metric label="Available" value={bid.available} /><Metric label="Terms" value={bid.terms} /><Metric label="Example evidence" value={bid.evidence} /></div>
                    <button type="button" disabled={selectedBid !== null} onClick={() => setSelectedBid(index)} className="mt-4 h-10 w-full bg-[#111315] text-xs font-extrabold text-white enabled:hover:bg-[#1748e5] disabled:bg-slate-200 disabled:text-slate-500">{selectedBid === index ? "Demo bid selected" : selectedBid === null ? "Accept demo bid" : "Example not selected"}</button>
                  </article>
                )) : <div className="border border-dashed border-slate-300 p-7 text-sm text-slate-500"><strong className="mb-2 block text-[#111315]">Example offers will arrive here</strong>The demo agent first clarifies the work, location and timing.</div>}
              </div>
              <p className="mt-4 text-xs leading-5 text-slate-500">{selectedBid !== null ? "Demo selection complete. In the signed-in app, Tessaris would now request explicit approval before booking or payment." : showBids ? "Three fictional example bids returned. Select one to see the protected hand-off." : "Illustrative demonstration · no real business is being contacted."}</p>
            </section>
          </div>
        </section>
      </Shell>
    </>
  );
}

function Brief({ label, value, wide = false }: { label: string; value: string; wide?: boolean }) {
  return <div className={`min-w-0 bg-[#f5f5f3] px-3 py-2 ${wide ? "col-span-2" : ""}`}><span className="mb-1 block text-[8px] uppercase tracking-[0.12em] text-slate-500">{label}</span><b className="block truncate text-xs">{value}</b></div>;
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div><span className="mb-1 block text-[8px] uppercase tracking-[0.11em] text-slate-500">{label}</span><b className="block text-[11px] leading-4">{value}</b></div>;
}

function MarketStep({ active, done, label, text }: { active: boolean; done: boolean; label: string; text: string }) {
  return <div className={`grid grid-cols-[64px_1fr] gap-2 py-1 transition-opacity ${active ? "opacity-100" : done ? "opacity-70" : "opacity-40"}`}><b className="text-[9px] uppercase tracking-[0.12em] text-[#1748e5]">{label}</b><span className="text-slate-600">{text}</span></div>;
}
