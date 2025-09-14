// Lightweight, non-strict types so we don't fight your TS settings.

export type PluginEventName =
  | "qfc:render-frame"
  | "qfc:glyph-hover"
  | "qfc:node-drag"
  | "codex:execution"
  | "codex:mutation"
  | "custom";

export interface PluginEvent<T = any> {
  type: PluginEventName | string;
  payload?: T;
  time?: number;
}

export interface ExecutionPayload {
  containerId?: string;
  code?: string;
  result?: any;
  meta?: Record<string, any>;
}

export interface MutationPayload {
  containerId?: string;
  kind?: string;
  before?: any;
  after?: any;
  score?: number;
  meta?: Record<string, any>;
}

export interface RenderContext {
  // r3f / three handles
  scene: any;
  camera: any;
  gl: any;

  // graph snapshot for the frame
  nodes?: any[];
  links?: any[];
}

export interface ExternalPlugin {
  id: string;            // unique
  name: string;
  version: string;

  // lifecycle
  initialize(): void | Promise<void>;
  dispose?(): void;

  // hooks (all optional)
  onEvent?(event: PluginEvent): void;
  onCodexExecution?(execution: ExecutionPayload): void;
  onMutation?(mutation: MutationPayload): void;
  onRenderFrame?(ctx: RenderContext): void;

  // optional HUD render (React node)
  renderHUD?(): any; // React.ReactNode but typed as any to avoid cross-bundle types
}

export interface PluginManifest {
  id: string;
  name: string;
  version: string;
  author?: string;
  description?: string;
  url?: string; // where it was loaded from
  capabilities?: string[];
}