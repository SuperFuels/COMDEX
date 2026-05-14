// src/components/TransportPicker.tsx
import { useEffect, useState } from "react";
import {
  getTransportMode,
  setTransportMode,
  type TransportMode,
} from "@glyphnet/utils/transport";

const OPTIONS: { value: TransportMode; label: string }[] = [
  { value: "auto",       label: "Auto" },
  { value: "radio-only", label: "Radio only" },
  { value: "ip-only",    label: "IP only" },
];

export default function TransportPicker() {
  const [mode, setMode] = useState<TransportMode>(getTransportMode());

  // keep local state in sync when some other part of the app changes the mode
  useEffect(() => {
    const onExt = (e: any) => setMode(e.detail as TransportMode);
    window.addEventListener("gnet:transport-mode", onExt);
    return () => window.removeEventListener("gnet:transport-mode", onExt);
  }, []);

  return (
    <select
      value={mode}
      onChange={(e) => setTransportMode(e.target.value as TransportMode)}
      title="Transport policy"
      style={{
        fontSize: 12,
        padding: "2px 6px",
        borderRadius: 6,
        border: "1px solid #e5e7eb",
        position: "relative",
        zIndex: 50, // keep above any badges/overlays
      }}
    >
      {OPTIONS.map(o => (
        <option key={o.value} value={o.value}>{o.label}</option>
      ))}
    </select>
  );
}