flowchart TD

%% =========================
%% QWAVE ENGINE CONTROL PANEL UPGRADE CHECKLIST
%% =========================

subgraph A[Ignition & Idle Detection]
  ✅ A1[ Add idle pulse lock: drift < threshold for ~20s]
  ✅ A2[ Integrate SQI metrics into ignition loop]
  ✅ A3[ Save & auto-load best idle state (BEST_IDLE.json)]
  ✅ A4[ Startup resonance trace: capture first 1000 ticks (res/drift/pulse/fields/particles)]
  ✅ A5[ Add --slowmode flag for readable ignition debug]
end

subgraph B[Gear Shift & Clutch Logic]
  ✅ B1[ Add pulse-gated gear shifting (field ramp only during pulse ticks)]
  ✅ B2[ Increase clutch ramp duration (5s → 20-30s)]
  ✅ B3[ Add sub-gear stepping (Idle → G1.5 → G2 to reduce collapse)]
  ✅ B4[ Auto-recover: reload idle after collapse instead of full reset]
  ✅ B5[ Apply drift dampener: "inner wall field" during gear ramp]
end

subgraph C[Particle Flow & Injector System]
  ✅ C1[ Build ParticleInjector class (intake → compress → fire)]
  ✅ C2[ Add CompressionChamber (tesseract container for density boost)]
  ✅ C3[ 4-Injector phased firing (offset cycles for smooth flow)]
  ✅ C4[ Gear-based injector tuning (rate & compression factor per gear)]
  ✅ C5[ Stage output flow: particles move downstream gear-to-gear]
end

subgraph D[Advanced Stabilization & Secondary Systems]
  ✅ D1[ Air Intake particle (Particle B) at plasma_excitation stage to counter decay]
  ✅ D2[ Auto drift-damp feedback: gravity/magnet tweaks on drift spike]
  ✅ D3[ Fuel injector phasing aligned to resonance peaks]
end

subgraph E[Logging & SQI Integration]
  ✅ E1[ Full SQI micro-analysis after runs (field avg recommendations)]
  ✅ E2[ Inline SQI drift + exhaust monitoring (real-time adjustments)]
  ✅ E3[ Ignition log JSON export (first 1000 ticks, tagged pulses)]
  ✅ E4[ Sync logs with test runner (QWave Control Panel ↔ Test Script)]
  ✅ E5[ Auto-plot resonance/drift/field history at end of run]
end

subgraph F[Multi-Gear Expansion]
  ✅ F1[ Extend to Gear 3+ (progressive compression & injector rates)]
  ⏳ F2[ Twin engine sync (dual ignition & gear linkage)]
  ⏳ F3[ Link exhaust flow into downstream chamber intake]
end