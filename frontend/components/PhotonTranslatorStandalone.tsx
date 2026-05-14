"use client";

import React from "react";

export default function PhotonTranslatorPanel({
  input,
  translation,
}: {
  input?: string;
  translation?: string;
}) {
  return (
    <div className="flex flex-col gap-1 text-xs font-mono text-zinc-300">
      <div className="text-zinc-500">Source:</div>
      <pre className="bg-neutral-950 p-2 rounded overflow-x-auto">{input}</pre>

      <div className="text-zinc-500 mt-2">Translation:</div>
      <pre className="bg-neutral-950 p-2 rounded text-indigo-300 overflow-x-auto">
        {translation || "⏳ waiting..."}
      </pre>
    </div>
  );
}