import type { TessarisTelemetry } from "@glyphnet/hooks/useTessarisTelemetry";

export type QFCMode = "gravity" | "tunnel" | "matter" | "connect" | "antigrav" | "sync";

export type QFCTheme = {
  gravity?: string;
  matter?: string;
  photon?: string;
  connect?: string;
  danger?: string;
  antigrav?: string;
  sync?: string;
};

export type QFCFlags = {
  nec_violation?: boolean;
  nec_strength?: number; // 0..1
  jump_flash?: number;   // 0..1
};

export type QFCFrame = {
  t: number;
  kappa?: number;
  chi?: number;
  sigma?: number;
  alpha?: number;
  curl_rms?: number;
  curv?: number;
  coupling_score?: number;
  max_norm?: number;
  mode?: QFCMode;
  theme?: QFCTheme;
  flags?: QFCFlags;
};

export type QFCViewportProps = {
  title?: string;
  subtitle?: string;
  rightBadge?: string;

  mode?: QFCMode;
  theme?: QFCTheme;

  frame?: QFCFrame | null;
  frames?: QFCFrame[];

  telemetry?: TessarisTelemetry;

  bloom?: boolean;
  bloomStrength?: number;
  bloomBlur?: number;
};