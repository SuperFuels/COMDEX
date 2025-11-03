// /src/lib/nav/router.ts
import type { Target } from "./parse";
import { resolveWormhole } from "../api/wormholes"; // resolves 🌀<name>.tp -> container record

// Open external http in system browser when running under Tauri
async function openExternal(url: string) {
  // @ts-ignore - runtime check for Tauri
  if (typeof window !== "undefined" && (window as any).__TAURI__) {
    const { open } = await import("@tauri-apps/api/shell");
    return open(url);
  }
  // Web: open in a new tab
  window.open(url, "_blank", "noopener,noreferrer");
}

export function routeNav(t: Target) {
  switch (t.kind) {
    case "http": {
      openExternal(t.href);
      return;
    }

    case "wormhole": {
      // Show the wormhole name immediately in the UI
      const hash = `#/wormhole/${encodeURIComponent(t.name)}`;
      if (window.location.hash !== hash) window.location.hash = hash;
      document.title = `🌀 ${t.name} — Glyph Net`;

      // Resolve to a concrete container in the background
      (async () => {
        try {
          const rec = await resolveWormhole(t.name);

          // Flip to the resolved container route so ContainerView mounts
          const id =
            rec.to ||
            rec.from ||
            (rec.name || t.name).replace(/\.tp$/i, "");
          const next = `#/container/${encodeURIComponent(id)}`;
          if (window.location.hash !== next) window.location.hash = next;

          // Notify any listeners (ContainerView, etc.)
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
  }
}