import React, { useState, useEffect } from 'react';
import AIONTerminal from '@/components/AIONTerminal';

export default function AIONDashboard() {
  const [leftWidth, setLeftWidth] = useState(400);
  const [isDragging, setIsDragging] = useState(false);

  const handleMouseDown = () => setIsDragging(true);

  const handleMouseMove = (e: MouseEvent) => {
    if (isDragging) {
      const newWidth = Math.max(200, Math.min(e.clientX, window.innerWidth - 300));
      setLeftWidth(newWidth);
    }
  };

  const handleMouseUp = () => setIsDragging(false);

  useEffect(() => {
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging]);

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Left Panel */}
      <div style={{ width: leftWidth }} className="bg-white p-4 overflow-y-auto border-r">
        <h2 className="text-xl font-semibold mb-4">🧠 AION Dashboard</h2>
        <p className="text-sm text-gray-500">
          Terminal now contains all input and output views.
        </p>
      </div>

      {/* Divider */}
      <div
        onMouseDown={handleMouseDown}
        className="w-1 bg-gray-300 cursor-col-resize"
        style={{ zIndex: 10 }}
      />

      {/* Right Panel: Terminal */}
      <div className="flex-1 h-full">
        <AIONTerminal />
      </div>
    </div>
  );
}