// 📦 File: backend/modules/visualization/beam_logic_packet_builder.ts

import { Glyph, Beam } from "../glyphwave/types/qfc";

interface LogicPacket {
  cause?: string;
  intent?: string;
  nextInference?: string;
  predictionConfidence?: number;
  symbolicAnchor?: string;
  errorTrace?: string;
}

/**
 * Build a logic packet to attach to a beam for QFC reasoning.
 */
export function build_logic_packet(
  sourceGlyph: Glyph,
  targetGlyph?: Glyph,
  options?: Partial<LogicPacket>
): LogicPacket {
  return {
    cause: sourceGlyph?.label ?? "Unknown",
    intent: options?.intent ?? `Link ${sourceGlyph.label} → ${targetGlyph?.label ?? "???"}`,
    nextInference: options?.nextInference ?? (targetGlyph?.prediction ?? undefined),
    predictionConfidence: options?.predictionConfidence ?? targetGlyph?.predictionConfidence ?? 0.5,
    symbolicAnchor: options?.symbolicAnchor ?? sourceGlyph?.id,
    errorTrace: options?.errorTrace ?? undefined,
  };
}

/**
 * Attaches logic packet to a QWave beam
 */
export function attach_logic_packet_to_beam(
  beam: Beam,
  packet: LogicPacket
): Beam {
  return {
    ...beam,
    metadata: {
      ...beam.metadata,
      logicPacket: packet,
    },
  };
}