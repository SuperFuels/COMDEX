// frontend/pages/aion/ContainerMap.tsx
import React, { useEffect, useState } from "react";
import dynamic from "next/dynamic";

const ContainerMap3D = dynamic(() => import("@/components/AION/ContainerMap3D"), {
  ssr: false,
  loading: () => <p className="text-white text-center mt-10">Loading 4D Container Map...</p>,
});

interface ContainerInfo {
  id: string;
  name: string;
  in_memory: boolean;
  connected: string[];
  glyph?: string;
  region?: string;
}

export default function ContainerMapPage() {
  const [containers, setContainers] = useState<ContainerInfo[]>([]);

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL}/aion/containers`)
      .then((res) => res.json())
      .then((data) => setContainers(data))
      .catch((err) => console.error("Failed to load containers:", err));
  }, []);

  return (
    <div className="h-screen w-screen bg-black overflow-hidden">
      <ContainerMap3D containers={containers} />
    </div>
  );
}