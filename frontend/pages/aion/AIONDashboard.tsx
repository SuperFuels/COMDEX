// Updated AION Dashboard Layout (Dashboard.tsx)
import React from 'react';
import { Button } from '@/components/ui/button';
import AIONTerminal from '@/components/AIONTerminal';

export default function AIONDashboard() {
  return (
    <div className="flex flex-col h-screen">
      {/* Main Container */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Section: Endpoint Controls */}
        <div className="w-1/3 p-4 overflow-y-auto bg-gray-50 border-r">
          <h2 className="text-xl font-bold mb-4">🧠 AION Controls</h2>

          {/* Each control as a card */}
          <div className="space-y-4">
            <div className="p-4 bg-white shadow rounded-xl">
              <h3 className="font-semibold mb-2">Dream Trigger</h3>
              <Button onClick={() => fetch('/api/aion/dream')}>Trigger Dream</Button>
            </div>

            <div className="p-4 bg-white shadow rounded-xl">
              <h3 className="font-semibold mb-2">Boot Skill</h3>
              <Button onClick={() => fetch('/api/aion/boot-skill')}>Boot Next Skill</Button>
            </div>

            <div className="p-4 bg-white shadow rounded-xl">
              <h3 className="font-semibold mb-2">Skill Reflect</h3>
              <Button onClick={() => fetch('/api/aion/skill-reflect')}>Reflect Skills</Button>
            </div>

            <div className="p-4 bg-white shadow rounded-xl">
              <h3 className="font-semibold mb-2">Dream Scheduler</h3>
              <Button onClick={() => fetch('/api/aion/run-dream')}>Run Scheduled Dream</Button>
            </div>
          </div>
        </div>

        {/* Right Section: Placeholder for Logs, Graphs, Future Widgets */}
        <div className="w-2/3 p-4 overflow-y-auto">
          <h2 className="text-xl font-bold mb-4">📊 AION Activity & Logs</h2>
          <div className="h-full bg-white border rounded-xl p-4 overflow-y-auto">
            {/* You can replace this with real-time log viewer or graph */}
            <p className="text-gray-500">AION system logs and visual output will appear here.</p>
          </div>
        </div>
      </div>

      {/* Terminal Footer */}
      <footer className="w-full bg-black text-white border-t border-gray-800 p-2">
        <AIONTerminal />
      </footer>
    </div>
  );
}