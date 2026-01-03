export type SimResult<TMetrics> = {
  metrics: TMetrics;
  traces?: Record<string, Float64Array>;
};

export type SimConfig = {
  dt: number; // seconds
  steps: number;
  seed: number;
};
