import React, { useState } from 'react';

export default function AIONTerminal() {
  const [leftLogs, setLeftLogs] = useState<string[]>([]);
  const [rightLogs, setRightLogs] = useState<string[]>([]);
  const [input, setInput] = useState('');

  const appendLeft = (msg: string) => setLeftLogs((prev) => [...prev, msg]);
  const appendRight = (msg: string) => setRightLogs((prev) => [...prev, msg]);

  const runEndpoint = async (endpoint: string) => {
    appendLeft(`▶️ Running ${endpoint}...`);
    try {
      const res = await fetch(`/api/aion/${endpoint}`);
      const data = await res.json();
      appendLeft(`✅ Response: ${JSON.stringify(data)}`);
    } catch (err) {
      appendLeft(`❌ Error: ${err}`);
    }
  };

  const sendPrompt = async () => {
    appendRight(`🧠 You: ${input}`);
    try {
      const res = await fetch('/api/aion', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: input }),
      });
      const data = await res.json();
      appendRight(`💬 AION: ${data.response}`);
    } catch (err) {
      appendRight(`❌ Error: ${err}`);
    }
    setInput('');
  };

  return (
    <div style={{ display: 'flex', height: '100%', flexDirection: 'column' }}>
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <div style={{ flex: 1, background: 'black', color: '#00FFCC', padding: '0.5rem', fontFamily: 'monospace', overflowY: 'auto' }}>
          {leftLogs.map((line, i) => <div key={i}>{line}</div>)}
        </div>
        <div style={{ flex: 1, background: 'black', color: '#00FFCC', padding: '0.5rem', fontFamily: 'monospace', overflowY: 'auto' }}>
          {rightLogs.map((line, i) => <div key={i}>{line}</div>)}
        </div>
      </div>

      <div style={{ display: 'flex', padding: '1rem', borderTop: '1px solid #ccc', background: '#f9f9f9' }}>
        <div style={{ flex: 1, display: 'flex', gap: '0.5rem' }}>
          <button className="bg-purple-600 text-white px-3 py-1 rounded" onClick={() => runEndpoint('boot-skill')}>🚀 Boot Skill</button>
          <button className="bg-yellow-500 text-white px-3 py-1 rounded" onClick={() => runEndpoint('skill-reflect')}>✨ Reflect</button>
          <button className="bg-green-600 text-white px-3 py-1 rounded" onClick={() => runEndpoint('run-dream')}>🌙 Run Dream</button>
          <button className="bg-indigo-600 text-white px-3 py-1 rounded" onClick={() => runEndpoint('game-dream')}>🎮 Game Dream</button>
        </div>
        <div style={{ flex: 1, display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask AION something..."
            style={{ flex: 1, padding: '0.5rem', border: '1px solid #ccc', borderRadius: '6px', fontFamily: 'monospace' }}
          />
          <button className="bg-black text-white px-3 py-1 rounded" onClick={sendPrompt}>Ask</button>
        </div>
      </div>
    </div>
  );
}