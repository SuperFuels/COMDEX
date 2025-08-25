awesome — here’s a drop-in, production-ready AtomMaxwell.tsx + tiny plumbing so the browser shell auto-mounts it when the container id is atom_maxwell. it’s lightweight, pretty, and works even if your WebSocket stream isn’t wired yet (it’ll fall back to a local mock).

1) frontend/components/Dimensions/AtomMaxwell.tsx


// frontend/components/Dimensions/AtomMaxwell.tsx
import { useEffect, useMemo, useRef, useState } from "react";
import { motion, useAnimation } from "framer-motion";
import { Play, Square, Gauge, Activity } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Slider } from "@/components/ui/slider";
import { Badge } from "@/components/ui/badge";
import useContainerStream, { ContainerEvent } from "@/hooks/useContainerStream";

type Props = {
  containerId: string;  // expected: "atom_maxwell"
};

export default function AtomMaxwell({ containerId }: Props) {
  const [running, setRunning] = useState(true);
  const [dilation, setDilation] = useState(600); // 1s wall = 10m subjective (600x)
  const [fieldE, setFieldE] = useState(0);
  const [fieldB, setFieldB] = useState(0);
  const [energy, setEnergy] = useState(0);

  // Live container events (falls back to local mock if no ws)
  const { last, connected } = useContainerStream(containerId, running, {
    mock: true,
    intervalMs: 120,
    mockFn: (t: number) => ({
      type: "field_update",
      data: {
        E: 0.7 * Math.sin(t / 600) + 0.3 * Math.sin(t / 137),
        B: 0.7 * Math.cos(t / 777) + 0.3 * Math.cos(t / 311),
        glyph: "∇×E = −∂B/∂t ; ∇×B = μ₀J + μ₀ε₀∂E/∂t",
      },
      meta: { dilation },
    } as ContainerEvent),
  });

  // Animation controls for particle loop
  const controls = useAnimation();
  const t0 = useRef<number>(performance.now());

  useEffect(() => {
    if (!running) return;
    let raf: number;
    const tick = () => {
      const t = performance.now() - t0.current;
      // simple internal animation loop even without events
      const e = 0.8 * Math.sin(t / 500) + 0.2 * Math.sin(t / 97);
      const b = 0.8 * Math.cos(t / 700) + 0.2 * Math.cos(t / 137);
      setEnergy(prev => 0.9 * prev + 0.1 * (e * e + b * b));
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [running]);

  // Apply incoming stream events
  useEffect(() => {
    if (!last) return;
    if (last.type === "field_update" && last.data) {
      setFieldE(last.data.E ?? fieldE);
      setFieldB(last.data.B ?? fieldB);
    }
  }, [last]);

  // Derived display
  const ePct = useMemo(() => Math.round(50 + 50 * fieldE), [fieldE]);
  const bPct = useMemo(() => Math.round(50 + 50 * fieldB), [fieldB]);
  const energyPct = useMemo(
    () => Math.max(0, Math.min(100, Math.round(100 * (1 - Math.exp(-energy))))),
    [energy]
  );

  // Particle ring params
  const N = 36;
  const particles = new Array(N).fill(0).map((_, i) => i);
  const radius = 120;
  const intensity = 0.5 + 0.5 * (Math.abs(fieldE) + Math.abs(fieldB)) / 2;

  return (
    <div className="p-6 w-full h-full grid grid-cols-1 xl:grid-cols-5 gap-6">
      {/* Left: Simulation */}
      <Card className="xl:col-span-3 rounded-2xl shadow-lg">
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-xl">Maxwell Field Chamber</CardTitle>
            <p className="text-sm text-muted-foreground">
              Container <Badge variant="secondary">{containerId}</Badge>
              <span className="ml-2">{connected ? "• live stream" : "• mock"}</span>
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant={running ? "secondary" : "default"}
              onClick={() => setRunning(r => !r)}
              className="rounded-2xl"
            >
              {running ? <><Square className="mr-2 h-4 w-4" /> Pause</> : <><Play className="mr-2 h-4 w-4" /> Run</>}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="relative mx-auto my-6 flex items-center justify-center" style={{ height: 360 }}>
            {/* EM Torus */}
            <div className="absolute inset-0 flex items-center justify-center">
              <motion.div
                animate={{ rotate: running ? 360 : 0, opacity: 0.9 }}
                transition={{ repeat: Infinity, duration: 12, ease: "linear" }}
                className="w-[300px] h-[300px] rounded-full"
                style={{
                  boxShadow: `0 0 60px rgba(99,102,241,${0.25 + intensity * 0.35}) inset, 0 0 80px rgba(16,185,129,${0.15 + intensity * 0.25})`,
                  background:
                    "radial-gradient(closest-side, rgba(255,255,255,0.06), rgba(99,102,241,0.12) 60%, transparent 70%)",
                  border: "1px solid rgba(255,255,255,0.08)",
                }}
              />
            </div>

            {/* Particle ring */}
            <div className="absolute inset-0 flex items-center justify-center">
              {particles.map(i => {
                const angle = (i / N) * Math.PI * 2;
                const x = radius * Math.cos(angle);
                const y = radius * Math.sin(angle);
                const size = 6 + 10 * intensity;
                return (
                  <motion.div
                    key={i}
                    animate={controls}
                    className="absolute rounded-full"
                    style={{
                      width: size,
                      height: size,
                      left: `calc(50% + ${x}px)`,
                      top: `calc(50% + ${y}px)`,
                      background: "rgba(99,102,241,0.9)",
                      boxShadow: `0 0 ${10 + 20 * intensity}px rgba(99,102,241,0.6)`,
                    }}
                  />
                );
              })}
            </div>

            {/* Readouts overlay */}
            <div className="absolute bottom-2 left-2 right-2 flex gap-4 justify-center">
              <Badge className="rounded-2xl">
                E-field: {ePct}%
              </Badge>
              <Badge className="rounded-2xl">
                B-field: {bPct}%
              </Badge>
              <Badge className="rounded-2xl">
                Energy: {energyPct}%
              </Badge>
            </div>
          </div>

          {/* Dilation + quick controls */}
          <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card className="rounded-2xl">
              <CardHeader className="py-3">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Gauge className="h-4 w-4" /> Time Dilation
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-0">
                <div className="text-xs text-muted-foreground mb-2">
                  1s wall = <span className="font-medium">{dilation}s</span> subjective
                </div>
                <Slider
                  min={60}
                  max={3600}
                  step={60}
                  value={[dilation]}
                  onValueChange={(v) => setDilation(v[0] ?? 600)}
                />
              </CardContent>
            </Card>

            <Card className="rounded-2xl">
              <CardHeader className="py-3">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Activity className="h-4 w-4" /> Trigger
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-0">
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    className="rounded-2xl"
                    onClick={() => sendCodexTrigger(containerId, "lean.replay", { nodes: ["maxwell_eqs"] })}
                  >
                    Replay (lean.replay)
                  </Button>
                  <Button
                    variant="outline"
                    className="rounded-2xl"
                    onClick={() => sendCodexTrigger(containerId, "pulse.wave", { amp: 0.2 })}
                  >
                    Pulse Wave
                  </Button>
                </div>
              </CardContent>
            </Card>

            <Card className="rounded-2xl">
              <CardHeader className="py-3">
                <CardTitle className="text-sm">Provenance</CardTitle>
              </CardHeader>
              <CardContent className="pt-0 text-sm">
                <div>caps: <code className="text-xs">["lean.replay","physics.maxwell"]</code></div>
                <div>nodes: <code className="text-xs">["maxwell_eqs","em_field"]</code></div>
                <div className="text-xs text-muted-foreground mt-1">renderer: AtomMaxwell</div>
              </CardContent>
            </Card>
          </div>
        </CardContent>
      </Card>

      {/* Right: State / glyphs */}
      <Card className="xl:col-span-2 rounded-2xl shadow-lg">
        <CardHeader>
          <CardTitle>Live Symbolic State</CardTitle>
          <p className="text-sm text-muted-foreground">
            Stream of container updates (compressed glyph view).
          </p>
        </CardHeader>
        <CardContent>
          <pre className="text-xs bg-black/40 rounded-xl p-3 overflow-auto max-h-[420px] border border-white/5">
{JSON.stringify(
  {
    connected,
    lastEvent: last?.type,
    lastData: last?.data,
    meta: { dilation },
  },
  null,
  2
)}
          </pre>
        </CardContent>
      </Card>
    </div>
  );
}

async function sendCodexTrigger(containerId: string, cap: string, payload: Record<string, any>) {
  try {
    // POST → your backend trigger endpoint (adjust if different)
    await fetch(`/api/container/${encodeURIComponent(containerId)}/trigger`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cap, payload }),
    });
  } catch (e) {
    // non-fatal
    console.warn("[AtomMaxwell] trigger failed:", e);
  }
}

