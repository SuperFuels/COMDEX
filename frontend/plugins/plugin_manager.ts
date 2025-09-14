// frontend/plugins/plugin_manager.ts
import type React from "react";
import { loadExternalPlugin } from "./external_plugin_loader";
import type {
  ExternalPlugin,
  PluginEvent,
  ExecutionPayload,
  MutationPayload,
  RenderContext,
  PluginManifest,
} from "./types";

type Listener = () => void;

class ExternalPluginManager {
  private plugins = new Map<string, ExternalPlugin>();
  private listeners = new Set<Listener>();

  /** Subscribe UI (e.g., PluginHUD) to state changes. Returns an unsubscribe. */
  subscribe(listener: Listener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private notify(): void {
    for (const l of this.listeners) l();
  }

  /** Simple list for status panels / debugging */
  list(): PluginManifest[] {
    return Array.from(this.plugins.values()).map((p) => ({
      id: p.id,
      name: p.name,
      version: p.version,
    }));
  }

  has(id: string): boolean {
    return this.plugins.has(id);
  }

  get(id: string): ExternalPlugin | undefined {
    return this.plugins.get(id);
  }

  /**
   * Load a plugin by URL (served from /public/plugins or remote).
   * Example: await pluginManager.loadFromUrl('/plugins/beam_highlighter.plugin.js')
   */
  async loadFromUrl(url: string): Promise<ExternalPlugin> {
    const plugin = await loadExternalPlugin(url);
    await this.register(plugin);
    return plugin;
  }

  /**
   * Load from a manifest object or manifest URL.
   * Minimal manifest: { id, name, version, url }
   */
  async loadFromManifest(manifestOrUrl: string | PluginManifest): Promise<ExternalPlugin> {
    let manifest: PluginManifest;

    if (typeof manifestOrUrl === "string") {
      const res = await fetch(manifestOrUrl);
      if (!res.ok) throw new Error(`Failed to fetch plugin manifest: ${manifestOrUrl}`);
      manifest = (await res.json()) as PluginManifest;
    } else {
      manifest = manifestOrUrl;
    }

    if (!manifest.url) throw new Error("Plugin manifest missing 'url' field");

    // Optional cache-bust in dev
    const u = new URL(manifest.url, typeof window !== "undefined" ? window.location.origin : "http://localhost");
    if (process.env.NODE_ENV !== "production") u.searchParams.set("v", Date.now().toString());

    const plugin = await loadExternalPlugin(u.toString());
    // Prefer manifest metadata if the plugin doesn't provide it
    plugin.id ||= manifest.id!;
    plugin.name ||= manifest.name!;
    plugin.version ||= manifest.version ?? "0.0.0";

    await this.register(plugin);
    return plugin;
  }

  /** Register (or hot-reload) a plugin instance. */
  async register(plugin: ExternalPlugin): Promise<void> {
    if (!plugin?.id) throw new Error("Plugin must have a stable 'id'");

    // hot-reload: dispose the old one if it exists
    const existing = this.plugins.get(plugin.id);
    if (existing?.dispose) {
      try {
        existing.dispose();
      } catch (err) {
        console.warn(`[plugin:${existing.id}] dispose error`, err);
      }
    }

    // allow async initialize
    try {
      await plugin.initialize?.();
    } catch (err) {
      console.error(`[plugin:${plugin.id}] initialize error`, err);
      // don't register a plugin that failed to init
      return;
    }

    this.plugins.set(plugin.id, plugin);
    this.notify();
  }

  /** Unload by id. */
  unload(id: string): void {
    const p = this.plugins.get(id);
    if (p?.dispose) {
      try {
        p.dispose();
      } catch (err) {
        console.warn(`[plugin:${id}] dispose error`, err);
      }
    }
    this.plugins.delete(id);
    this.notify();
  }

  /** Broadcast an arbitrary event (QFC/CodexLang/UI/etc.). */
  emit<T = unknown>(event: PluginEvent<T>): void {
    for (const p of this.plugins.values()) {
      try {
        p.onEvent?.(event);
      } catch (err) {
        console.warn(`[plugin:${p.id}] onEvent error`, err);
      }
    }
  }

  /** Per-frame callback (wire it from your render loop or RAF). */
  notifyRenderFrame(ctx: RenderContext): void {
    for (const p of this.plugins.values()) {
      try {
        p.onRenderFrame?.(ctx);
      } catch (err) {
        console.warn(`[plugin:${p.id}] onRenderFrame error`, err);
      }
    }
  }

  /** CodexLang execution hook. */
  broadcastCodexExecution(payload: ExecutionPayload): void {
    for (const p of this.plugins.values()) {
      try {
        p.onCodexExecution?.(payload);
      } catch (err) {
        console.warn(`[plugin:${p.id}] onCodexExecution error`, err);
      }
    }
  }

  /** Mutation hook. */
  broadcastMutation(payload: MutationPayload): void {
    for (const p of this.plugins.values()) {
      try {
        p.onMutation?.(payload);
      } catch (err) {
        console.warn(`[plugin:${p.id}] onMutation error`, err);
      }
    }
  }

  /**
   * Collect HUD nodes from plugins. Prefer React.ReactNode; fall back to any.
   * Use this from <PluginHUD/> to place plugin panels/overlays.
   */
  renderHUD(): React.ReactNode[] {
    const nodes: React.ReactNode[] = [];
    for (const p of this.plugins.values()) {
      try {
        const n = p.renderHUD?.();
        if (n) nodes.push(n);
      } catch (err) {
        console.warn(`[plugin:${p.id}] renderHUD error`, err);
      }
    }
    return nodes;
  }
}

export const pluginManager = new ExternalPluginManager();

/** Dev convenience in the browser console. */
if (typeof window !== "undefined") {
  // @ts-ignore
  window.SCI = {
    plugins: pluginManager,
    loadPlugin: (url: string) => pluginManager.loadFromUrl(url),
    loadManifest: (x: string) => pluginManager.loadFromManifest(x),
    list: () => pluginManager.list(),
    unload: (id: string) => pluginManager.unload(id),
  };
  console.info("🧩 SCI plugin API available as window.SCI (loadPlugin/loadManifest/list/unload)");
}

// Re-export types for consumers importing from this module.
export type {
  ExternalPlugin,
  PluginEvent,
  ExecutionPayload,
  MutationPayload,
  RenderContext,
  PluginManifest,
};