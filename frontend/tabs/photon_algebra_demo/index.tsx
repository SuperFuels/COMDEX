"use client";

import PhotonHero from "./PhotonHero";
import PhotonTheoremGrid from "./PhotonTheoremGrid";
import PhotonWorkbench from "./PhotonWorkbench";

export default function PhotonAlgebraDemoTab() {
  return (
    <div className="w-full space-y-10">
      <PhotonHero />
      <PhotonTheoremGrid />
      <PhotonWorkbench />
    </div>
  );
}