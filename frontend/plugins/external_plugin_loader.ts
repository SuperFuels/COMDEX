import type { ExternalPlugin } from "./types";

// Dynamic ESM import from URL or relative path.
// Works in dev/Next; cache-bust param avoids stale chunks in hot reload.
export async function loadExternalPlugin(url: string): Promise<ExternalPlugin> {
  const withBust = url.includes("?") ? `${url}&t=${Date.now()}` : `${url}?t=${Date.now()}`;
  const mod: any = await import(/* webpackIgnore: true */ withBust);
  const plugin: ExternalPlugin = (mod?.default || mod) as ExternalPlugin;

  if (!plugin || !plugin.id || !plugin.initialize) {
    throw new Error(`Invalid plugin at ${url} — must export default ExternalPlugin`);
  }
  return plugin;
}