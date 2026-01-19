// frontend/tabs/Aion/index.tsx
"use client";

import React from "react";
import AionProofOfLifeDashboard from "./AionProofOfLifeDashboard";
import AionCognitiveDashboard from "./AionCognitiveDashboard";

export default function AionTab() {
  return (
    <section className="space-y-16 pb-24">
      <AionProofOfLifeDashboard />
      <AionCognitiveDashboard />
    </section>
  );
}