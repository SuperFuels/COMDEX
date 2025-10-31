// frontend/components/ReplayControls.tsx
import { applyReplay } from "@/lib/api";
import { useHUDPulse } from "@/hooks/useHUDPulse";

interface ReplayControlsProps {
  frames: any[];  // For now — later we make a ReplayFrame type
}

export function ReplayControls({ frames }: ReplayControlsProps) {
  const pulse = useHUDPulse("restore");

  return (
    <button
      className="btn-primary"
      onClick={async () => {
        await applyReplay(frames);
        pulse(); // ✅ success HUD pulse
      }}
    >
      Apply Replay
    </button>
  );
}