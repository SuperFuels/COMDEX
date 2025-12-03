// src/lib/types/holo.ts

// --- Basic ids --------------------------------------------------------------

export type HoloId = string;       // "holo:container/<cid>/t=1234/v1"

// If ContainerId is exported from dc.ts, you can import it like this:
//   import type { ContainerId } from "./dc";
// For now just alias it to string to keep this file standalone:
export type ContainerId = string;  // UCS/KG container id

export type HoloKind =
  | "memory"
  | "sandbox"
  | "crystal"
  | "library"
  | "snapshot"
  | "program"
  | string;

export type HoloSourceView = "code" | "kg" | "qfc" | "summary" | string;

// --- Core Holo IR -----------------------------------------------------------

export interface HoloIR {
  // ── Identity & lineage ─────────────────────────────
  holo_id: HoloId;
  container_id: ContainerId;
  name?: string;
  symbol?: string; // e.g. "⚛", "◆", etc.
  kind?: HoloKind;

  origin: {
    created_at: string; // ISO-8601
    created_by: "aion" | "user" | "system" | string;
    reason?: string; // "export_from_devtools", "timefold_snapshot", ...
    source_view?: HoloSourceView;
    parent_holo_id?: HoloId; // for forks / versions
    container_snapshot_id?: string; // vault snapshot, if available
  };

  version: {
    major: number;
    minor: number;
    patch: number;
    revision: number; // monotonic, for quick comparisons
    lineage?: string[]; // previous holo_ids in the chain
  };

  // ── Graph / GHX layout (from KG pack / container glyph_grid) ──
  ghx: {
    nodes: Array<{
      id: string;
      label?: string;
      type?: string; // "kg_node", "file", "module", "atom", ...
      tags?: string[];
      // visual/layout hints:
      pos?: { x: number; y: number; z?: number };
      icon?: string; // UI icon id or emoji
      meta?: Record<string, any>; // any KG meta (domain, topics, etc)
    }>;
    edges: Array<{
      id?: string;
      src: string;
      dst: string;
      relation: string; // "uses", "entangled_with", "about", ...
      weight?: number;
      tags?: string[];
      meta?: Record<string, any>;
    }>;
    // global viz hints
    layout?: "grid" | "atom" | "hoberman" | "custom" | string;
    ghx_mode?: "hologram" | "shell" | "expanding_sphere" | string;
    overlay_layers?: string[]; // e.g. ["electron_rings", "symbolic_expansion"]
    entangled_links?: string[]; // other container_ids this is linked to
  };

  // ── Field physics: ψκT + QQC/SLE state ──────────────
  field: {
    // Logical tensor/field state; intentionally loose but stable.
    psi_kappa_T: {
      frame: "original" | "mutated" | "replay" | string;
      state_vector?: Record<string, any>;
      harmonics?: Record<string, any>;
      invariants?: Record<string, any>;
    };

    // Scalar metrics from QQC / SLE / beam runtime
    metrics: {
      coherence: number; // 0..1
      drift: number; // normalized drift (e.g. 0..1)
      entropy?: number;
      sqi?: number; // structural quality index if available
      logic_score?: number; // from logic prediction / Codex metrics
      tick?: number; // ContainerRuntime.tick_counter at capture
      execution_time_ms?: number; // for run_holo
    };

    // Optional snapshots of engine-specific state
    qqc_state?: {
      kernel_version?: string;
      mode?: string;
      status?: "idle" | "executing" | "completed" | "error";
      last_event_id?: string;
      meta?: Record<string, any>;
    };

    sle_state?: {
      runtime_id?: string;
      last_opcode?: string;
      // any coherence/collapse info from BeamRuntime / SLE path
      meta?: Record<string, any>;
    };
  };

  // ── Beams / photonics (QWave) ───────────────────────
  beams: Array<{
    beam_id: string;
    source_id?: string;
    target_id?: string;
    carrier_type?: string; // "SIMULATED", "VIRTUAL", etc.
    modulation_strategy?: string; // "SimPhase", etc.
    coherence?: number;
    entangled_path?: string[]; // list of container_ids / nodes
    mutation_trace?: any[];
    collapse_state?: string;
    metadata?: Record<string, any>;
  }>;

  // Mirrors container["qwave_beams"] / container["symbolic"]["qwave_beams"]
  multiverse_frame?: string; // "original", "mutated", etc.

  // ── Views / lenses for DevTools QFC ─────────────────
  views: {
    code_view?: {
      files?: string[]; // paths or ids
      entry_file?: string;
      ast_root_id?: string; // if you have AST graph ids
      selection?: string; // node id / symbol at capture
    };

    kg_view?: {
      focus_node_id?: string;
      filters?: string[]; // tags / domains
    };

    qfc_view?: {
      camera?: {
        position: [number, number, number];
        target: [number, number, number];
        zoom?: number;
      };
      highlighted_nodes?: string[];
      highlighted_beams?: string[];
      hud_overlays?: string[]; // active overlay ids
    };

    summary_view?: {
      title?: string;
      text?: string; // natural-language summary / caption
      tags?: string[];
    };
  };

  // ── Indexing + patterns ─────────────────────────────
  indexing: {
    tags: string[];
    patterns?: Array<{
      pattern_id: string;
      name?: string;
      sqi_score?: number;
      kind?: string; // "loop", "refactor", "error_cluster", ...
    }>;
    topic_vector?: number[]; // from sqi_fastmap
  };

  // ── Timefold / snapshots ────────────────────────────
  timefold?: {
    tick: number; // tick at capture
    t_label?: string; // "before_refactor", "after_QQC_run", ...
    snapshot_ref?: string; // Vault snapshot id / path
    previous_tick?: number | null;
    next_tick?: number | null;
  };

  // ── Ledger / provenance / security ──────────────────
  ledger?: {
    tx_id?: string; // for hologram_state_transition events
    thread_id?: string; // e.g. "kg:personal:ucs://local/ucs_hub"
    topic_wa?: string;
    event_ids?: string[]; // ids in kg_events
  };

  security?: {
    soullaw_status?: "allowed" | "blocked" | "test_only" | "unknown";
    signatures?: Array<{
      signer: string; // "vault://user/..", "agent:qqc_kernel", ...
      algorithm: string; // "ed25519", ...
      signature: string; // base64, hex, etc.
    }>;
  };

  // ── Sandbox / collab flags ──────────────────────────
  sandbox?: {
    is_sandbox: boolean;
    promotion_status?: "pending" | "rejected" | "promoted";
  };

  collaboration?: {
    shared: boolean;
    session_id?: string;
    authors?: string[]; // ids / names
    cursors?: Array<{
      actor_id: string;
      node_id?: string;
      coord?: [number, number, number];
      color?: string;
    }>;
    comments?: Array<{
      id: string;
      author: string;
      node_id?: string;
      text: string;
      created_at: string;
      reply_to?: string;
    }>;
    history_ref?: string; // pointer to change-log / glyph_trace
  };

  // ── Raw refs (no big blobs) ─────────────────────────
  references?: {
    container_kg_export?: string; // path to *.kg.json if saved
    container_dc_path?: string; // underlying .dc.json path
    qqc_run_id?: string;
    sle_run_id?: string;
  };

  // Room for extensions
  extra?: Record<string, any>;
}