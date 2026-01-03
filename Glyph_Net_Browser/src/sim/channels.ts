/**
 * Stage B — Response channels (measurable outputs)
 * Keep these generic so they apply across proxy models (P0/P1/P2...).
 */

export type ResponseChannels = {
  // per-node scalar response (energy/amplitude proxy)
  amp?: number[];

  // per-node phase (if model supports it)
  phase?: number[];

  // global lock/coherence proxy (e.g. Kuramoto order parameter R)
  lock?: number;

  // routing success / score (later P12 schedule tests)
  routing_success?: number; // 0..1

  // geometry error (later cluster/rigidity tests)
  geometry_error?: number; // >=0
};

export type ChannelFrame = {
  t: number;
  ch: ResponseChannels;
};

export function lastFrame(frames: ChannelFrame[]) {
  return frames.length ? frames[frames.length - 1] : null;
}
