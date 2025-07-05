import React, { useState, useEffect } from 'react';
import AIONTerminal from '@/components/AIONTerminal';

export default function AIONDashboard() {
  const [leftWidth, setLeftWidth] = useState(400);
  const [isDragging, setIsDragging] = useState(false);
  const [status, setStatus] = useState<any>(null);
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

  const handleButtonClick = async (endpoint: string, label: string) => {
    try {
      const res = await fetch(`/api/aion/${endpoint}`);
      const data = await res.json();
      setResponse(`${label} Result:\n${data.result || JSON.stringify(data)}`);
    } catch (err) {
      setResponse(`${label} Result:\n❌ Error triggering ${label.toLowerCase()}.`);
    }
  };

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Left Panel */}
      <div style={{ width: leftWidth }} className="bg-white p-4 overflow-y-auto border-r">
        <h2 className="text-xl font-semibold mb-4">🧠 AION Controls</h2>

        {status && (
          <div className="mb-4 text-sm font-mono text-gray-800">
            <p>
              <strong>Unlocked Modules:</strong>{' '}
              <span className="text-green-600">{status.unlocked?.join(', ')}</span>
            </p>
            <p>
              <strong>Locked Modules:</strong>{' '}
              <span className="text-red-600">{status.locked?.join(', ')}</span>
            </p>
          </div>
        )}

        <div className="space-y-2">
          <button onClick={() => handleButtonClick('run-dream', 'Run Dream')} className="w-full bg-blue-500 text-white py-2 rounded">Trigger Dream</button>
          <button onClick={() => handleButtonClick('boot-skill', 'Boot Skill')} className="w-full bg-blue-500 text-white py-2 rounded">Boot Next Skill</button>
          <button onClick={() => handleButtonClick('skill-reflect', 'Reflect')} className="w-full bg-blue-500 text-white py-2 rounded">Reflect Skills</button>
          <button onClick={() => handleButtonClick('run-dream?game=true', 'Game Dream')} className="w-full bg-blue-500 text-white py-2 rounded">Run Scheduled Dream</button>
        </div>

        <h2 className="text-xl font-semibold mt-6 mb-2">📡 Endpoints</h2>
        <div className="space-y-2">
          <button onClick={() => handleButtonClick('boot-skills', 'Summarize unlocked skills')} className="w-full bg-gray-200 py-2 rounded">Summarize unlocked skills</button>
          <button onClick={() => handleButtonClick('goal', 'Show goal progress')} className="w-full bg-gray-200 py-2 rounded">Show goal progress</button>
          <button onClick={() => handleButtonClick('reflect', 'Reflect on recent dreams')} className="w-full bg-gray-200 py-2 rounded">Reflect on recent dreams</button>
          <button onClick={() => handleButtonClick('boot-skills', 'List bootloader queue')} className="w-full bg-gray-200 py-2 rounded">List bootloader queue</button>
          <button onClick={() => handleButtonClick('identity', 'Personality Profile')} className="w-full bg-gray-200 py-2 rounded">What is my current personality profile?</button>
        </div>

        {response && (
          <div className="mt-4 bg-gray-50 p-2 border rounded text-sm font-mono whitespace-pre-wrap">
            {response}
          </div>
        )}
      </div>

      <div onMouseDown={handleMouseDown} className="w-1 bg-gray-300 cursor-col-resize" style={{ zIndex: 10 }} />

      {/* Right Panel: Terminal */}
      <div className="flex-1 h-full">
        <AIONTerminal />
      </div>
    </div>
  );
}