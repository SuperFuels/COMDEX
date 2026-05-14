import type { SimConfig, SimResult } from "./types";

export type StepFn = (step: number, t: number) => void;

export function runSim<TMetrics>(
  cfg: SimConfig,
  stepFn: StepFn,
  finalize: () => TMetrics,
): SimResult<TMetrics> {
  const { dt, steps } = cfg;
  let t = 0;
  for (let i = 0; i < steps; i++) {
    stepFn(i, t);
    t += dt;
  }
  return { metrics: finalize() };
}
