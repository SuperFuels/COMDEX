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
          <AIONTerminal side="left" />
        </div>
        <div
          className="w-1 bg-gray-300 cursor-col-resize"
          onMouseDown={startDrag}
          onMouseUp={stopDrag}
        />
        <div className="overflow-auto" style={{ width: `${100 - leftWidth}%` }}>
          <AIONTerminal side="right" />
        </div>
      </div>

      <footer className="flex justify-between items-center bg-white border-t p-3 text-sm">
        <div className="flex gap-2 items-center">
          <button className="bg-blue-600 text-white px-3 py-1 rounded" onClick={() => window.dispatchEvent(new CustomEvent('aion-command', { detail: 'status' }))}>Status</button>
          <button className="bg-blue-600 text-white px-3 py-1 rounded" onClick={() => window.dispatchEvent(new CustomEvent('aion-command', { detail: 'goal' }))}>Goal</button>
          <button className="bg-blue-600 text-white px-3 py-1 rounded" onClick={() => window.dispatchEvent(new CustomEvent('aion-command', { detail: 'identity' }))}>Identity</button>
          <button className="bg-blue-600 text-white px-3 py-1 rounded" onClick={() => window.dispatchEvent(new CustomEvent('aion-command', { detail: 'situation' }))}>Situation</button>
          <button className="bg-purple-600 text-white px-3 py-1 rounded" onClick={() => window.dispatchEvent(new CustomEvent('aion-command', { detail: 'boot-skill' }))}>🧠 Boot Skill</button>
          <button className="bg-yellow-500 text-white px-3 py-1 rounded" onClick={() => window.dispatchEvent(new CustomEvent('aion-command', { detail: 'reflect' }))}>🪞 Reflect</button>
          <button className="bg-green-600 text-white px-3 py-1 rounded" onClick={() => window.dispatchEvent(new CustomEvent('aion-command', { detail: 'run-dream' }))}>💤 Run Dream</button>
          <button className="bg-indigo-600 text-white px-3 py-1 rounded" onClick={() => window.dispatchEvent(new CustomEvent('aion-command', { detail: 'game-dream' }))}>🎮 Game Dream</button>
          <span className="ml-2 px-2 py-1 border rounded text-gray-600">Dream Visualizer</span>
        </div>
      </footer>
    </div>
  );
}