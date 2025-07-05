import React, { useState } from 'react';
import AIONTerminal from '@/components/AIONTerminal';

export default function AIONDashboard() {
  const [leftWidth, setLeftWidth] = useState(400);
  const [isDragging, setIsDragging] = useState(false);

  const handleMouseDown = () => {
    setIsDragging(true);
  };

  const handleMouseMove = (e: MouseEvent) => {
    if (isDragging) {
      const newWidth = Math.max(200, Math.min(e.clientX, window.innerWidth - 300));
      setLeftWidth(newWidth);
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  React.useEffect(() => {
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging]);

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Left Panel: Controls and Endpoints */}
      <div style={{ width: leftWidth }} className="bg-white p-4 overflow-y-auto border-r">
        <h2 className="text-xl font-semibold mb-4">🛠️ Controls</h2>
        <div className="space-y-2">
          <button className="w-full bg-blue-500 text-white py-2 rounded">Trigger Dream</button>
          <button className="w-full bg-blue-500 text-white py-2 rounded">Boot Next Skill</button>
          <button className="w-full bg-blue-500 text-white py-2 rounded">Reflect Skills</button>
          <button className="w-full bg-blue-500 text-white py-2 rounded">Run Scheduled Dream</button>
        </div>

        <h2 className="text-xl font-semibold mt-6 mb-4">📡 Endpoints</h2>
        <div className="space-y-2">
          <button className="w-full bg-gray-200 py-2 rounded">Summarize unlocked skills</button>
          <button className="w-full bg-gray-200 py-2 rounded">Show goal progress</button>
          <button className="w-full bg-gray-200 py-2 rounded">Reflect on recent dreams</button>
          <button className="w-full bg-gray-200 py-2 rounded">List bootloader queue</button>
          <button className="w-full bg-gray-200 py-2 rounded">What is my current personality profile?</button>
        </div>
      </div>

      {/* Divider */}
      <div
        onMouseDown={handleMouseDown}
        className="w-1 bg-gray-300 cursor-col-resize"
        style={{ zIndex: 10 }}
      />

      {/* Right Panel: Terminal only */}
      <div className="flex-1 h-full">
        <AIONTerminal />
      </div>
    </div>
  );
}