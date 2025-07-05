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
      <div className="flex flex-1 overflow-hidden">
        <div className="overflow-auto" style={{ width: `${leftWidth}%` }}>
          <AIONTerminal />
        </div>
        <div
          className="w-1 bg-gray-300 cursor-col-resize"
          onMouseDown={startDrag}
          onMouseUp={stopDrag}
        />
        <div className="overflow-auto" style={{ width: `${100 - leftWidth}%` }}>
          <AIONTerminal />
        </div>
      </div>

      <footer className="flex justify-between items-center bg-white border-t p-3 text-sm">
        <div className="flex gap-2 items-center">
          <button className="bg-blue-600 text-white px-3 py-1 rounded">Status</button>
          <button className="bg-blue-600 text-white px-3 py-1 rounded">Goal</button>
          <button className="bg-blue-600 text-white px-3 py-1 rounded">Identity</button>
          <button className="bg-blue-600 text-white px-3 py-1 rounded">Situation</button>
          <span className="text-gray-500 ml-4">🌙 Dream Visualizer (Coming Soon)</span>
        </div>
        <div className="flex gap-2 items-center">
          <input
            className="border border-gray-300 px-3 py-1 rounded w-64"
            placeholder="Type your command..."
          />
          <button className="bg-indigo-600 text-white px-4 py-1 rounded">Ask</button>
        </div>
      </footer>
    </div>
  );
}