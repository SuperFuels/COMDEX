// pages/aion/AIONDashboard.tsx

import React, { useRef, useState } from 'react';
import AIONTerminal from '@/components/AIONTerminal';

export default function AIONDashboard() {
  const [leftWidth, setLeftWidth] = useState(50);
  const containerRef = useRef<HTMLDivElement>(null);
  const isDragging = useRef(false);

  const startDrag = () => (isDragging.current = true);
  const stopDrag = () => (isDragging.current = false);

  const handleDrag = (e: React.MouseEvent) => {
    if (!isDragging.current || !containerRef.current) return;
    const containerWidth = containerRef.current.offsetWidth;
    const newLeftWidth = (e.clientX / containerWidth) * 100;
    if (newLeftWidth > 10 && newLeftWidth < 90) {
      setLeftWidth(newLeftWidth);
    }
  };

  return (
    <div className="flex flex-col h-screen">
      {/* Main Split Container */}
      <div
        className="flex flex-1 overflow-hidden"
        ref={containerRef}
        onMouseMove={handleDrag}
        onMouseUp={stopDrag}
      >
        {/* Left Terminal */}
        <div className="flex flex-col" style={{ width: `${leftWidth}%` }}>
          <div className="flex-1 overflow-auto border-r border-gray-200">
            <AIONTerminal side="left" />
          </div>
        </div>

        {/* Divider */}
        <div
          className="w-1 bg-gray-300 cursor-col-resize"
          onMouseDown={startDrag}
          onMouseUp={stopDrag}
        />

        {/* Right Terminal */}
        <div className="flex flex-col" style={{ width: `${100 - leftWidth}%` }}>
          <div className="flex-1 overflow-auto">
            <AIONTerminal side="right" />
          </div>
        </div>
      </div>

      {/* Footer Controls */}
      <footer className="bg-white border-t px-4 py-3 flex justify-between items-center text-sm">
        {/* Left Button Controls */}
        <div className="flex gap-2 flex-wrap">
          <button className="bg-blue-600 text-white px-3 py-1 rounded">Status</button>
          <button className="bg-blue-600 text-white px-3 py-1 rounded">Goal</button>
          <button className="bg-blue-600 text-white px-3 py-1 rounded">Identity</button>
          <button className="bg-blue-600 text-white px-3 py-1 rounded">Situation</button>
          <button className="bg-purple-600 text-white px-3 py-1 rounded">🧠 Boot Skill</button>
          <button className="bg-yellow-400 text-white px-3 py-1 rounded">🌀 Reflect</button>
          <button className="bg-green-600 text-white px-3 py-1 rounded">🌙 Run Dream</button>
          <button className="bg-indigo-600 text-white px-3 py-1 rounded">🎮 Game Dream</button>
          <button className="border px-3 py-1 rounded">Dream Visualizer</button>
        </div>

        {/* Terminal Indicator (optional) */}
        <div className="text-gray-400 italic">AION Dashboard</div>
      </footer>
    </div>
  );
}