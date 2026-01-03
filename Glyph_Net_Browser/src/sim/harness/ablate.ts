import type { TokenKind, WaveProgram, WaveToken } from "../lexicon";
import { normalizeProgram } from "../lexicon";

export type Ablation = {
  label: string;

  // remove all tokens of this kind (e.g. remove "ω" to kill addressing)
  dropTokenKind?: TokenKind;

  // remove env.gate01 overrides (keeps topology gate external)
  dropGateEnv?: boolean;

  // drop all τ windows (forces always-active if program relies on τ)
  dropTimeWindows?: boolean;
};

export function ablateProgram(programLike: WaveProgram | WaveToken[], ab: Ablation): WaveProgram {
  const p = normalizeProgram(programLike);

  const tokens = p.tokens.filter((tok) => {
    if (ab.dropTokenKind && tok.kind === ab.dropTokenKind) return false;
    if (ab.dropGateEnv && tok.kind === "env" && (tok as any).gate01 != null) return false;
    if (ab.dropTimeWindows && tok.kind === "τ") return false;
    return true;
  });

  return { name: p.name, tokens };
}

export function makeAblations(defaults?: Partial<Ablation>): Ablation[] {
  // canonical Stage B ablations
  const base: Ablation[] = [
    { label: "drop_ω", dropTokenKind: "ω" },
    { label: "drop_A", dropTokenKind: "A" },
    { label: "drop_φ", dropTokenKind: "φ" },
    { label: "drop_p", dropTokenKind: "p" },
    { label: "drop_m", dropTokenKind: "m" },
    { label: "drop_τ", dropTimeWindows: true },
    { label: "drop_env_gate", dropGateEnv: true },
  ];
  return defaults ? base.map((b) => ({ ...b, ...defaults })) : base;
}
