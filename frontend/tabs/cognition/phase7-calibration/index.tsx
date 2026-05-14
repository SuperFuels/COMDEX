"use client";

import React from "react";
import Phase7CalibrationHUD from "./Phase7CalibrationHUD";

export default function Phase7CalibrationTab() {
  return (
    <section className="space-y-16">
      {/* HERO */}
      <div className="text-center space-y-6">
        <h1 className="text-7xl md:text-9xl font-bold tracking-tight text-black italic">
          Phase 7
        </h1>
        <p className="text-2xl text-gray-500 font-light tracking-tight">
          Expectation Calibration —{" "}
          <span className="text-black font-medium">trust in confidence.</span>
        </p>
        <p className="max-w-3xl mx-auto text-lg text-gray-500 leading-relaxed">
          Post-hoc, read-only calibration analysis: reliability curve, ECE, bin gaps,
          and deterministic lock verification against the committed golden bundle.
        </p>
      </div>

      {/* HUD */}
      <div className="max-w-6xl mx-auto">
        <Phase7CalibrationHUD />
      </div>

      {/* PITCH */}
      <div className="grid md:grid-cols-2 gap-12 border-t border-gray-100 pt-24">
        <div className="space-y-8">
          <div className="space-y-4">
            <h2 className="text-3xl font-bold italic tracking-tight">
              What It Proves
            </h2>
            <p className="text-gray-600 leading-relaxed">
              Phase 7 measures whether AION’s expressed confidence matches empirical
              accuracy under fixed thresholds. No learning. No tuning. Just measurement
              + certification.
            </p>
          </div>

          <div className="bg-gray-50 p-8 rounded-[2.5rem] border border-gray-100">
            <h4 className="text-sm font-bold uppercase tracking-widest text-amber-600 mb-4">
              Outputs
            </h4>
            <p className="text-sm text-gray-500 leading-relaxed">
              <strong>reliability_curve.json</strong>, <strong>calibration_metrics.json</strong>,
              plus <strong>.lock.json</strong> sanitized artifacts and a{" "}
              <strong>phase7_lock_bundle.json</strong> with SHA256.
            </p>
          </div>
        </div>

        <div className="space-y-12">
          <div className="p-8 rounded-[2.5rem] bg-black text-white">
            <h4 className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-500 mb-2">
              The Vision
            </h4>
            <p className="text-xl font-medium italic leading-snug">
              "Not just predictions — provable honesty about uncertainty."
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}