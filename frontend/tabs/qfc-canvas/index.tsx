"use client";

import React from "react";
import QfcCanvasDemo from "./qfc_demo";

export default function QfcCanvasTab() {
  return (
    <section className="space-y-16">
      {/* 1) HERO */}
      <div className="text-center space-y-6">
        <h1 className="text-7xl md:text-9xl font-bold tracking-tight text-black italic">
          Quantum Field Canvas
        </h1>

        <p className="text-2xl text-gray-500 font-light tracking-tight">
          QFC HUD + Field Lab —{" "}
          <span className="text-black font-medium">live scenario control + telemetry.</span>
        </p>

        <p className="max-w-3xl mx-auto text-lg text-gray-500 leading-relaxed">
          A full-screen, live QFC canvas that reuses the existing DevTools QFC stack
          (telemetry hook + HUD + scenario knobs) without duplicating logic.
        </p>
      </div>

      {/* 2) LIVE CANVAS */}
      <div className="max-w-6xl mx-auto">
        <QfcCanvasDemo />
      </div>

      {/* 3) PITCH / NOTES */}
      <div className="grid md:grid-cols-2 gap-12 border-t border-gray-100 pt-24">
        <div className="space-y-8">
          <h2 className="text-3xl font-bold italic tracking-tight">What you’re seeing</h2>
          <p className="text-gray-600 leading-relaxed">
            This tab mounts the same QFC HUD panel used in DevTools, but as a dedicated
            “canvas” experience. It preserves querystring parameters (e.g. container=dc_aion_core)
            so you can deep-link a specific container/scenario.
          </p>

          <div className="bg-gray-50 p-8 rounded-[2.5rem] border border-gray-100">
            <h4 className="text-sm font-bold uppercase tracking-widest text-amber-600 mb-4">
              Live feed dependency
            </h4>
            <p className="text-sm text-gray-500 leading-relaxed">
              The canvas expects the same telemetry feed as DevTools QFC. If the feed is stale,
              treat it as a real pipeline failure (not a UI problem).
            </p>
          </div>
        </div>

        <div className="space-y-12">
          <div className="p-8 rounded-[2.5rem] bg-black text-white">
            <h4 className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-500 mb-2">
              Operator mode
            </h4>
            <p className="text-xl font-medium italic leading-snug">
              “This is the control surface: scenarios in, telemetry out, and the field renders
              the consequence in realtime.”
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}