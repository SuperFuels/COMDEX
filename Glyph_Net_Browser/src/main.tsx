// src/main.tsx
import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App";

// Optional: Safari AudioContext shim (no-op elsewhere)
if (typeof window !== "undefined" &&
    !(window as any).AudioContext &&
    (window as any).webkitAudioContext) {
  (window as any).AudioContext = (window as any).webkitAudioContext;
}

const el = document.getElementById("root");
if (!el) throw new Error("Root element #root not found");

// Avoid StrictMode here to prevent double effects with media devices in dev
createRoot(el).render(<App />);