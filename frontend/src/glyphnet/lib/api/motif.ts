// src/lib/api/motif.ts
import type { GhxPacket } from "../../components/DevFieldHologram3D";
import type { HoloIR } from "../types/holo";

export type MotifCompileResponse = {
  kind: string;        // e.g. "photon_motif"
  ghx: GhxPacket;
  holo?: HoloIR | null;
};

export async function compileMotifStub(
  source: string,
  opts: { holo?: boolean } = {},
): Promise<MotifCompileResponse> {
  const res = await fetch("/api/motif/compile", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      source,
      options: { holo: !!opts.holo },
    }),
  });

  if (!res.ok) {
    // Try JSON { detail: ... } first, then plain text
    let detail = "";
    try {
      const data = await res.json();
      if (data && typeof data.detail === "string") {
        detail = data.detail;
      }
    } catch {
      try {
        detail = await res.text();
      } catch {
        /* ignore */
      }
    }

    throw new Error(detail || `HTTP ${res.status}`);
  }

  return (await res.json()) as MotifCompileResponse;
}