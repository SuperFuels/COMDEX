// frontend/tabs/symatics/index.tsx
"use client";

import Hero from "./Hero";
import ResonanceWorkbench from "./ResonanceWorkbench";
import PaperViewer from "./PaperViewer";

export default function SymaticsTab() {
  return (
    <>
      <Hero />

      <div className="mt-16">
        <ResonanceWorkbench />
      </div>

      <PaperViewer />
    </>
  );
}