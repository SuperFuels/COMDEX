import { useEffect, useState, useCallback } from "react";

type Status = {
  tick: number;
  playing: boolean;
  ratio: number;
  loop_enabled?: boolean;
  loop_range?: [number, number];
  decay_enabled?: boolean;
};

export default function TimeControls({
  containerId,
  status: externalStatus,
}: {
  containerId: string;
  status?: Partial<Status> | null;
}) {
  const [status, setStatus] = useState<Status>({
    tick: 0,
    playing: false,
    ratio: 1,
    loop_enabled: false,
    loop_range: [0, 0],
    decay_enabled: false,
  });

  // Merge in external status (from GHX updates)
  useEffect(() => {
    if (!externalStatus) return;
    setStatus((s) => ({ ...s, ...externalStatus } as Status));
  }, [externalStatus]);

  const fetchStatus = useCallback(async () => {
    const r = await fetch(`/api/aion/time/${encodeURIComponent(containerId)}/status`);
    if (r.ok) {
      const json = await r.json();
      setStatus((s) => ({
        ...s,
        tick: json.tick ?? s.tick,
        playing: json.playing ?? s.playing,
        ratio: json.ratio ?? s.ratio,
        loop_enabled: json.loop_enabled ?? s.loop_enabled,
        loop_range: json.loop_range ?? s.loop_range,
        decay_enabled: json.decay_enabled ?? s.decay_enabled,
      }));
    }
  }, [containerId]);

  useEffect(() => {
    if (!containerId) return;
    fetchStatus();
  }, [containerId, fetchStatus]);

  const play = async (ratio: number) => {
    await fetch(`/api/aion/time/${encodeURIComponent(containerId)}/play`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ratio }),
    });
    fetchStatus();
  };

  const pause = async () => {
    await fetch(`/api/aion/time/${encodeURIComponent(containerId)}/pause`, { method: "POST" });
    fetchStatus();
  };

  const tick = async () => {
    await fetch(`/api/aion/time/${encodeURIComponent(containerId)}/tick`, { method: "POST" });
    fetchStatus();
  };

  const rewind = async (to: number) => {
    await fetch(`/api/aion/time/${encodeURIComponent(containerId)}/rewind`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tick: to }),
    });
    fetchStatus();
  };

  const [ratio, setRatio] = useState<number>(1);
  useEffect(() => setRatio(status.ratio), [status.ratio]);

  const [rewindTo, setRewindTo] = useState<string>("0");

  return (
    <div style={{ display: "flex", gap: 8, alignItems: "center", fontSize: 12 }}>
      <span style={{ fontWeight: 600 }}>Time</span>
      {/* Play / Pause / Tick */}
      {status.playing ? (
        <button
          onClick={pause}
          style={{ padding: "4px 8px", borderRadius: 6, border: "1px solid #e5e7eb", background: "#fee2e2" }}
        >
          ⏸ Pause
        </button>
      ) : (
        <button
          onClick={() => play(ratio)}
          style={{ padding: "4px 8px", borderRadius: 6, border: "1px solid #e5e7eb", background: "#dcfce7" }}
        >
          ▶️ Play
        </button>
      )}
      <button
        onClick={tick}
        style={{ padding: "4px 8px", borderRadius: 6, border: "1px solid #e5e7eb", background: "#f8fafc" }}
      >
        ⏩ Tick
      </button>

      {/* Ratio */}
      <label style={{ marginLeft: 8 }}>speed:</label>
      <input
        type="range"
        min={0.25}
        max={4}
        step={0.25}
        value={ratio}
        onChange={(e) => setRatio(parseFloat(e.target.value))}
        onMouseUp={() => (!status.playing ? null : play(parseFloat(String(ratio))))}
        onTouchEnd={() => (!status.playing ? null : play(parseFloat(String(ratio))))}
        style={{ width: 120 }}
      />
      <span>{ratio.toFixed(2)}×</span>

      {/* Tick readout + rewind */}
      <span style={{ marginLeft: 12 }}>tick: {status.tick}</span>
      <input
        value={rewindTo}
        onChange={(e) => setRewindTo(e.target.value)}
        placeholder="rewind→tick"
        style={{ width: 90, padding: "3px 6px", borderRadius: 6, border: "1px solid #e5e7eb" }}
      />
      <button
        onClick={() => rewind(Math.max(0, parseInt(rewindTo || "0", 10)))}
        style={{ padding: "4px 8px", borderRadius: 6, border: "1px solid #e5e7eb", background: "#f1f5f9" }}
      >
        ⏪ Rewind
      </button>
    </div>
  );
}