// src/main.tsx
import "@/lib/radioPatch";   // ← MUST be first: rewrites ws/http calls to VITE_RADIO_BASE

import React from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import AppRoutes from "./routes";

// Optional Safari AudioContext shim
if (
  typeof window !== "undefined" &&
  !(window as any).AudioContext &&
  (window as any).webkitAudioContext
) {
  (window as any).AudioContext = (window as any).webkitAudioContext;
}

// --- QKD debug flag ---
;(window as any).__QKD_E2EE = import.meta.env.VITE_QKD_E2EE;
console.info("[QKD] E2EE flag =", import.meta.env.VITE_QKD_E2EE);

// --- QKD fetch interceptor (encrypt only POST /api/glyphnet/tx) ---
import { protectCapsule } from "./lib/qkd_wrap";
const E2EE = import.meta.env.VITE_QKD_E2EE === "1";

if (E2EE) {
  const origFetch = window.fetch.bind(window);
  window.fetch = async (input: any, init?: RequestInit) => {
    try {
      const url =
        typeof input === "string"
          ? input
          : input?.url
          ? String(input.url)
          : String(input);

      const isPost = (init?.method || "GET").toUpperCase() === "POST";
      const isGlyphTx = /\/api\/glyphnet\/tx$/.test(url);
      const hasStringBody = typeof init?.body === "string";

      if (isPost && isGlyphTx && hasStringBody) {
        const body = JSON.parse(init!.body as string);

        const recipient = String(body?.recipient || "");
        const graph = String(body?.graph || "personal").toLowerCase();
        const capsule = body?.capsule ?? {};
        const meta = body?.meta ?? {};

        const { capsule: protectedCapsule } = await protectCapsule({
          capsule,
          localWA: meta?.localWA || "ucs://local/self",
          remoteWA: recipient,
          kg: graph,
        });

        const localWA = meta?.localWA || "ucs://local/self";
        const nextMeta = { ...meta, qkd_required: true, localWA, recipient };

        init = {
          ...init,
          body: JSON.stringify({ ...body, capsule: protectedCapsule, meta: nextMeta }),
        };

        console.debug("[QKD] protected /api/glyphnet/tx");
      }
    } catch (e) {
      console.warn("[QKD] fetch shim skipped:", e);
    }
    return origFetch(input, init);
  };
}

// Mount app with real routes ("/" and "/dev/rf")
const el = document.getElementById("root");
if (!el) throw new Error("Root element #root not found");

createRoot(el).render(
  <React.StrictMode>
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  </React.StrictMode>
);