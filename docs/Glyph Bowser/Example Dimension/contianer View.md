3) Wire it into the browser shell (one small change)

Add a special renderer mapping where you choose which dimension component to mount. Example in your ContainerView.tsx (or wherever you resolve the renderer):


// frontend/components/Browser/ContainerView.tsx
import dynamic from "next/dynamic";
import DimensionRenderer from "@/components/Dimensions/DimensionRenderer";

// Lazy-load the special renderer to keep bundle small
const AtomMaxwell = dynamic(() => import("@/components/Dimensions/AtomMaxwell"), { ssr: false });

type Props = { containerId: string };

export default function ContainerView({ containerId }: Props) {
  const specialMap: Record<string, React.ComponentType<{ containerId: string }>> = {
    atom_maxwell: AtomMaxwell,
  };

  const Renderer = specialMap[containerId] ?? DimensionRenderer;
  return <Renderer containerId={containerId} />;
}






5) Tiny backend notes (only if you want live data today)
	•	WebSocket stream (optional): expose GET /ws/container/{id} that emits JSON messages like:


{"type":"field_update","data":{"E":0.31,"B":-0.12},"meta":{"dilation":600}}


