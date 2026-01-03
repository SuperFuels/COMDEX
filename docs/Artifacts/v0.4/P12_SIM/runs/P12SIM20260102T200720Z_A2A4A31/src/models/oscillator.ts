import { randn } from "../rng";

export type Oscillator = {
  // state
  x: number;
  v: number;
  // params
  w0: number;   // natural angular frequency (rad/s)
  zeta: number; // damping ratio
  gain: number; // drive gain
};

export type OscillatorBank = {
  oscs: Oscillator[];
};

export function makeOscillatorBank(opts: {
  freqsHz: number[];
  zeta?: number;
  gain?: number;
}): OscillatorBank {
  const zeta = opts.zeta ?? 0.08;
  const gain = opts.gain ?? 1.0;

  return {
    oscs: opts.freqsHz.map((f) => ({
      x: 0,
      v: 0,
      w0: 2 * Math.PI * f,
      zeta,
      gain,
    })),
  };
}

export function stepOscillators(
  bank: OscillatorBank,
  dt: number,
  u: number,
  noiseStd: number,
  rng: () => number,
) {
  for (const o of bank.oscs) {
    // x'' + 2 zeta w0 x' + w0^2 x = gain * u + noise
    const a =
      o.gain * u +
      noiseStd * randn(rng) -
      2 * o.zeta * o.w0 * o.v -
      (o.w0 * o.w0) * o.x;

    o.v += a * dt;
    o.x += o.v * dt;
  }
}

export function oscEnergy(o: Oscillator) {
  // frequency-normalized amplitude proxy:
  // for x=A sin(ωt), v=Aω cos(ωt) => (v/ω)^2 + x^2 ≈ A^2
  const w = Math.max(1e-9, Math.abs(o.w0));
  const vn = o.v / w;
  return o.x * o.x + vn * vn;
}