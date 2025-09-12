// File: frontend/lib/sqiColors.ts

// 🎨 Map SQI levels to beam stroke colors
export const SQIColorMap: Record<number, string> = {
  0: "#cccccc", // 🟤 Neutral / No SQI
  1: "#00ffff", // 🟦 Low coherence
  2: "#00ff88", // 🟢 Moderate coherence
  3: "#ffff00", // 🟡 Aligned with prediction
  4: "#ff8800", // 🟠 Strong entanglement
  5: "#ff0000", // 🔴 High symbolic intensity
  6: "#aa00ff", // 🟣 Holographic resonance
  7: "#ffffff", // ⚪️ Peak SQI (Symbolic Quantum Supremacy)
};