"use client";

import WirePackWorkbench from "./WirePackWorkbench";

export default function WirePackTab() {
  return (
    <>
      <Hero />
      <div className="mt-16">
        <WirePackWorkbench />
      </div>
    </>
  );
}

function Hero() {
  return (
    <div className="pt-10">
      <div className="text-xs font-bold text-gray-300 uppercase tracking-widest">
        GlyphOS Transport Layer
      </div>
      <h1 className="text-3xl font-semibold text-gray-800 mt-2">WirePack</h1>
      <p className="text-sm text-gray-500 mt-3 max-w-2xl">
        Start with v46 streaming transport, then switch demos (transport / analytics / trust)
        using the workbench controls.
      </p>
    </div>
  );
}