import React from "react";

interface RegisterDebugProps {
  trace: {
    step: number;
    instruction: string;
    before: Record<string, any>;
    after: Record<string, any>;
  }[];
}

export default function CodexRegisterDebug({ trace }: RegisterDebugProps) {
  if (!trace?.length) return null;

  return (
    <div className="bg-gray-900 p-4 rounded-md text-white space-y-4">
      <h3 className="text-cyan-400 font-bold text-lg">🔬 Register Debug Trace</h3>
      {trace.map((entry) => (
        <div key={entry.step} className="border border-cyan-600 p-3 rounded-md">
          <div className="text-cyan-300 font-semibold">Step {entry.step} — {entry.instruction}</div>
          <div className="grid grid-cols-2 gap-4 mt-2">
            <div>
              <div className="text-cyan-200 font-semibold mb-1">Before</div>
              <pre className="bg-gray-800 p-2 rounded-md text-sm">
                {JSON.stringify(entry.before, null, 2)}
              </pre>
            </div>
            <div>
              <div className="text-green-300 font-semibold mb-1">After</div>
              <pre className="bg-gray-800 p-2 rounded-md text-sm">
                {JSON.stringify(entry.after, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}