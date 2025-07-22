import React from "react";
import dynamic from "next/dynamic";

const MonacoDiffEditor = dynamic(
  () => import("react-monaco-editor").then(mod => mod.DiffEditor),
  { ssr: false }
);

interface CodexDiffViewerProps {
  original: string;
  mutated: string;
}

export default function CodexDiffViewer({ original, mutated }: CodexDiffViewerProps) {
  return (
    <div className="mt-6 border border-purple-700 rounded-md overflow-hidden">
      <h3 className="bg-purple-800 text-white text-sm px-4 py-2 font-semibold">
        🧬 Scroll Mutation Diff
      </h3>
      <MonacoDiffEditor
        language="json"
        original={original}
        value={mutated}
        theme="vs-dark"
        options={{
          readOnly: true,
          automaticLayout: true,
          wordWrap: "on",
        }}
        height="400"
      />
    </div>
  );
}