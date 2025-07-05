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
    <div
      className="flex flex-col h-screen"
      ref={containerRef}
      onMouseMove={handleDrag}
      onMouseUp={stopDrag}
    >
      {/* Main split view */}
      <div className="flex flex-1 overflow-hidden">
        <div className="overflow-auto p-4" style={{ width: `${leftWidth}%` }}>
          <AIONTerminal side="left" />
        </div>
        <div
          className="w-1 bg-gray-300 cursor-col-resize"
          onMouseDown={startDrag}
          onMouseUp={stopDrag}
        />
        <div className="overflow-auto p-4" style={{ width: `${100 - leftWidth}%` }}>
          <AIONTerminal side="right" />
        </div>
      </div>

      {/* Fixed Footer with Controls */}
      <footer className="flex justify-between items-center bg-white border-t p-3 text-sm fixed bottom-0 left-0 w-full z-50">
        <div className="flex gap-2 items-center">
          <button className="bg-blue-600 text-white px-3 py-1 rounded">Status</button>
          <button className="bg-blue-600 text-white px-3 py-1 rounded">Goal</button>
          <button className="bg-blue-600 text-white px-3 py-1 rounded">Identity</button>
          <button className="bg-blue-600 text-white px-3 py-1 rounded">Situation</button>
          <button className="bg-purple-600 text-white px-3 py-1 rounded">🔁 Boot Skill</button>
          <button className="bg-yellow-500 text-white px-3 py-1 rounded">🪞 Reflect</button>
          <button className="bg-green-600 text-white px-3 py-1 rounded">🌙 Run Dream</button>
          <button className="bg-indigo-600 text-white px-3 py-1 rounded">🎮 Game Dream</button>
          <button className="bg-gray-300 px-3 py-1 rounded">Dream Visualizer</button>
        </div>
      </footer>
    </div>
  );
}