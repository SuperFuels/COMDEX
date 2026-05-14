import { applyReplay } from "@/lib/api";
import { useHUDPulse as useHUDPulseRaw } from "@/hooks/useHUDPulse";

interface ReplayControlsProps {
  frames: any[];
}

export function ReplayControls({ frames }: ReplayControlsProps) {
  // Normalize the hook result into a callable `pulse`
  const hud: any = useHUDPulseRaw("restore");
  const pulse: () => void =
    typeof hud === "function"
      ? hud
      : typeof hud?.pulse === "function"
      ? hud.pulse
      : (Array.isArray(hud) && typeof hud[0] === "function"
          ? hud[0]
          : () => {}); // no-op fallback

  return (
    <button
      className="btn-primary"
      onClick={async () => {
        await applyReplay(frames);
        pulse(); // ✅ always callable
      }}
    >
      Apply Replay
    </button>
  );
}