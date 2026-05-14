import { randn } from "../rng";

export type Node = {
  id: string;
  x: number;
  y: number;
  w: number;      // natural angular frequency (rad/s)
  theta: number;  // phase
};

export type Edge = {
  a: number;
  b: number;
  k: number; // coupling strength (pre-distance)
};

export type KuramotoNet = {
  nodes: Node[];
  edges: Edge[];
};

export function makeKuramotoNet(opts: {
  positions: Array<{ x: number; y: number }>;
  wHz?: number;
  wJitterHz?: number;
  seedTheta?: number;
}): KuramotoNet {
  const wHz = opts.wHz ?? 1.0;
  const wJitterHz = opts.wJitterHz ?? 0.02;

  return {
    nodes: opts.positions.map((p, i) => ({
      id: `n${i}`,
      x: p.x,
      y: p.y,
      w: 2 * Math.PI * (wHz + (i % 2 ? wJitterHz : -wJitterHz)),
      theta: opts.seedTheta ?? 0,
    })),
    edges: [],
  };
}

function dist(a: Node, b: Node) {
  const dx = a.x - b.x;
  const dy = a.y - b.y;
  return Math.sqrt(dx * dx + dy * dy);
}

export function addEdge(net: KuramotoNet, a: number, b: number, k: number) {
  net.edges.push({ a, b, k });
}

export function stepKuramoto(
  net: KuramotoNet,
  dt: number,
  cfg: {
    kGlobal: number;      // overall coupling scale
    distScale: number;    // distance falloff
    noiseStd: number;
    rng: () => number;
    kLinkEnabled: boolean;
    kLinkPairs: Array<[number, number]>;
    kLinkStrength: number;
  },
) {
  const { nodes, edges } = net;

  const hasKLink = (i: number, j: number) => {
    for (const [a, b] of cfg.kLinkPairs) {
      if ((a === i && b === j) || (a === j && b === i)) return true;
    }
    return false;
  };

  const dtheta = new Float64Array(nodes.length);

  for (let i = 0; i < nodes.length; i++) {
    const ni = nodes[i];
    let sum = 0;

    for (const e of edges) {
      if (e.a !== i && e.b !== i) continue;
      const j = e.a === i ? e.b : e.a;
      const nj = nodes[j];

      let k = e.k;

      if (cfg.kLinkEnabled && hasKLink(i, j)) {
        k = cfg.kLinkStrength; // override removes distance decay
      } else {
        const d = dist(ni, nj);
        k = k * Math.exp(-d / cfg.distScale);
      }

      sum += k * Math.sin(nj.theta - ni.theta);
    }

    dtheta[i] = ni.w + cfg.kGlobal * sum + cfg.noiseStd * randn(cfg.rng);
  }

  for (let i = 0; i < nodes.length; i++) {
    nodes[i].theta += dtheta[i] * dt;
  }
}

export function orderParameter(net: KuramotoNet) {
  // Kuramoto R in [0,1]
  let cx = 0, sx = 0;
  for (const n of net.nodes) {
    cx += Math.cos(n.theta);
    sx += Math.sin(n.theta);
  }
  cx /= net.nodes.length;
  sx /= net.nodes.length;
  return Math.sqrt(cx * cx + sx * sx);
}
