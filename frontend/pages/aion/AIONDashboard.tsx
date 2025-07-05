// AIONDashboard.tsx
import React from 'react';
import AIONTerminal from '../../components/AIONTerminal';

export default function AIONDashboard() {
  return (
    <div className="flex h-screen pt-16">
      {/* Left Terminal */}
      <div className="w-1/2 border-r border-gray-200 p-2 overflow-hidden">
        <AIONTerminal side="left" />
      </div>

      {/* Right Terminal */}
      <div className="w-1/2 p-2 overflow-hidden">
        <AIONTerminal side="right" />
      </div>
    </div>
  );
}