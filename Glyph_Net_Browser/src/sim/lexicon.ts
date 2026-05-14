/**
 * Stage B — Lexicon v0 (locked contract)
 * Wave alphabet tokens used by the sim harness (and later P13 compiler).
 *
 * Tokens v0: ω, A, φ, p, m(x), τ, env
 * - Interpretation: "last token of a kind wins" (within active τ windows).
 * - τ is a time window gate; outside all τ windows, u(t)=0 by default.
 * - env is metadata (noise/drift/gate) used by harness/models.
 */

export type TokenKind = "ω" | "A" | "φ" | "p" | "m" | "τ" | "env";

export type OmegaToken = { kind: "ω"; hz: number };
export type AmpToken = { kind: "A"; value: number }; // nominal amplitude scalar
export type PhaseToken = { kind: "φ"; rad: number }; // phase in radians
export type ParityToken = { kind: "p"; value: 1 | -1 }; // protocol header / parity bit
export type ModeToken = {
  kind: "m";
  mode: string; // e.g. "plane" | "gaussian" | "custom"
  params?: Record<string, number>;
};
export type TimeWindowToken = {
  kind: "τ";
  t0: number; // seconds (inclusive)
  t1: number; // seconds (exclusive)
};
export type EnvToken = {
  kind: "env";
  noiseStd?: number; // default harness/model noise
  drift?: number; // default drift
  gate01?: number; // topo gate override (0..1), if desired by harness
};

export type WaveToken =
  | OmegaToken
  | AmpToken
  | PhaseToken
  | ParityToken
  | ModeToken
  | TimeWindowToken
  | EnvToken;

export type WaveProgram = {
  name?: string;
  tokens: WaveToken[];
};

export type ProgramState = {
  omegaHz: number;
  amp: number;
  phaseRad: number;
  parity: 1 | -1;
  mode: string;
  modeParams: Record<string, number>;
  gate01: number; // 0..1
  noiseStd?: number;
  drift?: number;
  active: boolean; // τ gating result
};

export const TOKEN_SET_V0: readonly TokenKind[] = ["ω", "A", "φ", "p", "m", "τ", "env"] as const;

export function clamp01(v: number) {
  return Math.max(0, Math.min(1, v));
}

export function normalizeProgram(p: WaveProgram | WaveToken[]): WaveProgram {
  return Array.isArray(p) ? { tokens: p } : p;
}

/**
 * Compile-time-ish evaluation: interpret tokens at time t.
 * Returns scalar drive u(t) + decoded header state for metrics/logging.
 */
export function applyProgramAtTime(
  programLike: WaveProgram | WaveToken[],
  t: number,
  defaults?: Partial<ProgramState>,
): { u: number; state: ProgramState } {
  const program = normalizeProgram(programLike);

  // defaults (safe + deterministic)
  const st: ProgramState = {
    omegaHz: defaults?.omegaHz ?? 1,
    amp: defaults?.amp ?? 1,
    phaseRad: defaults?.phaseRad ?? 0,
    parity: defaults?.parity ?? 1,
    mode: defaults?.mode ?? "plane",
    modeParams: defaults?.modeParams ?? {},
    gate01: clamp01(defaults?.gate01 ?? 1),
    noiseStd: defaults?.noiseStd,
    drift: defaults?.drift,
    active: true,
  };

  // τ windows (if any exist, you must be inside >=1 to be active)
  let hasWindows = false;
  let inWindow = false;

  for (const tok of program.tokens) {
    switch (tok.kind) {
      case "τ":
        hasWindows = true;
        if (t >= tok.t0 && t < tok.t1) inWindow = true;
        break;
      case "ω":
        st.omegaHz = tok.hz;
        break;
      case "A":
        st.amp = tok.value;
        break;
      case "φ":
        st.phaseRad = tok.rad;
        break;
      case "p":
        st.parity = tok.value;
        break;
      case "m":
        st.mode = tok.mode;
        st.modeParams = tok.params ?? {};
        break;
      case "env":
        if (tok.noiseStd != null) st.noiseStd = tok.noiseStd;
        if (tok.drift != null) st.drift = tok.drift;
        if (tok.gate01 != null) st.gate01 = clamp01(tok.gate01);
        break;
      default: {
        const _exhaustive: never = tok;
        void _exhaustive;
      }
    }
  }

  st.active = hasWindows ? inWindow : true;

  // Base scalar waveform: u(t) = A * sin(2π ω t + φ)
  // (Mode is metadata for now; later it shapes spatial programs.)
  const u = st.active ? st.amp * Math.sin(2 * Math.PI * st.omegaHz * t + st.phaseRad) : 0;

  return { u, state: st };
}
