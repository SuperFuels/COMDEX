// File: frontend/components/QuantumField/beam_reroute.ts

/**
 * Reroutes a beam path through a cognitive focus point (if available),
 * and optionally adds glow intensity based on memory weight.
 */

export function rerouteBeam(
  source: [number, number, number],
  target: [number, number, number],
  focusPoint?: [number, number, number]
): [number, number, number][] {
  if (!focusPoint) return [source, target];
  return [source, focusPoint, target];
}

export function getBeamGlowIntensity(memoryWeight: number): number {
  if (memoryWeight >= 1.0) return 1.0;
  if (memoryWeight >= 0.8) return 0.8;
  if (memoryWeight >= 0.5) return 0.6;
  return 0.3;
}