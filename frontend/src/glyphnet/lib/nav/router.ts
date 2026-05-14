// src/lib/nav/router.ts
import type { Target } from "./parse";
import { resolveWormhole } from "../api/wormholes"; // keeps async resolution

// Open external http in system browser when running under Tauri
async function openExternal(url: string) {
  // Web: open in a new tab
  if (typeof window !== "undefined") {
    window.open(url, "_blank", "noopener,noreferrer");
  }
}

export function routeNav(t: Target) {
  switch (t.kind) {
    case "http": {
      openExternal(t.href);
      return;
    }

    case "wormhole": {
      // 1) Show the wormhole name immediately
      const hash = `#/wormhole/${encodeURIComponent(t.name)}`;
      if (window.location.hash !== hash) window.location.hash = hash;
      document.title = `🌀 ${t.name} — Glyph Net`;

      // 2) Resolve → flip to concrete container (best-effort)
      (async () => {
        try {
          const rec = await resolveWormhole(t.name);
          const id =
            rec.to ||
            rec.from ||
            (rec.name || t.name).replace(/\.tp$/i, "");
          const next = `#/container/${encodeURIComponent(id)}`;
          if (window.location.hash !== next) window.location.hash = next;

          window.dispatchEvent(new CustomEvent("wormhole:resolved", { detail: rec }));
        } catch (err) {
          window.dispatchEvent(
            new CustomEvent("wormhole:resolve_error", {
              detail: { name: t.name, error: String(err) },
            })
          );
        }
      })();
      return;
    }

    case "dimension": {
      const hash = `#/dimension/${encodeURIComponent(t.path)}`;
      if (window.location.hash !== hash) window.location.hash = hash;
      document.title = `dimension://${t.path} — Glyph Net`;
      return;
    }

    case "container": {                               // ⬅️ NEW
      const hash = `#/container/${encodeURIComponent(t.id)}`;
      if (window.location.hash !== hash) window.location.hash = hash;
      document.title = `${t.id} — Container • Glyph Net`;
      // Optional: notify listeners
      window.dispatchEvent(new CustomEvent("container:navigate", { detail: { id: t.id } }));
      return;
    }
  }
}