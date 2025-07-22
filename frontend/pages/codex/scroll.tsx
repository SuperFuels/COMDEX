// 📁 pages/codex/scroll.tsx

import React from "react";
import dynamic from "next/dynamic";

const CodexScrollRunner = dynamic(
  () => import("@/components/Codex/CodexScrollRunner"),
  { ssr: false }
);

export default function CodexScrollPage() {
  return (
    <div className="p-6 min-h-screen bg-black text-white">
      <h1 className="text-3xl font-bold mb-4">📜 Codex Scroll Executor</h1>
      <p className="mb-6 text-gray-400">
        Input a symbolic CodexLang scroll and execute it via the Codex Virtual CPU.
      </p>
      <CodexScrollRunner />
    </div>
  );
}