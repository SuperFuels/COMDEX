// frontend/pages/aion/AIONDashboard.tsx
import React, { useState, useEffect } from 'react';
import AIONTerminal from '@/components/AIONTerminal';

export default function AIONDashboard() {
  const [leftWidth, setLeftWidth] = useState(400);
  const [isDragging, setIsDragging] = useState(false);
  const [response, setResponse] = useState('');

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

  const handleClick = async (endpoint: string) => {
    setResponse('⌛ Loading...');
    try {
      const res = await fetch(`/api/aion/${endpoint}`);
      const data = await res.json();
      setResponse(data.result || JSON.stringify(data));
    } catch (err) {
      setResponse('❌ Error fetching from ' + endpoint);
    }
  };

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Left Control Panel */}
      <div style={{ width: leftWidth }} className="bg-white p-4 border-r overflow-y-auto">
        <h2 className="text-xl font-semibold mb-4">🧠 AION Dashboard</h2>
        <p className="text-sm text-gray-500 mb-4">Control buttons populate below.</p>

        <div className="space-y-3">
          <button onClick={() => handleClick('boot-skill')} className="w-full bg-purple-600 text-white py-2 rounded shadow">🌀 Boot Skill</button>
          <button onClick={() => handleClick('reflect')} className="w-full bg-yellow-500 text-white py-2 rounded shadow">🔮 Reflect</button>
          <button onClick={() => handleClick('run-dream')} className="w-full bg-green-600 text-white py-2 rounded shadow">🌙 Run Dream</button>
          <button onClick={() => handleClick('game-dream')} className="w-full bg-indigo-600 text-white py-2 rounded shadow">🎮 Game Dream</button>
        </div>

        {/* Response from button clicks */}
        {response && (
          <div className="mt-4 bg-gray-100 p-3 border rounded text-sm font-mono whitespace-pre-wrap max-h-[50vh] overflow-y-auto">
            {response}
          </div>
        )}
      </div>

      {/* Drag divider */}
      <div onMouseDown={handleMouseDown} className="w-1 bg-gray-300 cursor-col-resize" />

      {/* Right Terminal View */}
      <div className="flex-1 h-full">
        <AIONTerminal />
      </div>
    </div>
  );
}