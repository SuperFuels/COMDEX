// frontend/pages/aion/AIONDashboard.tsx

import React, { useState } from 'react';
import dynamic from 'next/dynamic';
import Split from 'react-split';
import styles from '@/styles/AIONDashboard.module.css';
import { Button } from '@/components/ui/button';

const AIONTerminal = dynamic(() => import('@/components/AIONTerminal'), { ssr: false });

export default function AIONDashboard() {
  const [leftLogs, setLeftLogs] = useState<string[]>([]);
  const [rightLogs, setRightLogs] = useState<string[]>([]);
  const [input, setInput] = useState('');

  const appendLeft = (msg: string) => setLeftLogs((prev) => [...prev, msg]);
  const appendRight = (msg: string) => setRightLogs((prev) => [...prev, msg]);

  const runEndpoint = async (endpoint: string) => {
    appendLeft(`▶️ ${endpoint}...`);
    try {
      const res = await fetch(`/api/aion/${endpoint}`);
      const data = await res.json();
      appendLeft(`✅ ${endpoint}: ${JSON.stringify(data)}`);
    } catch (e) {
      appendLeft(`❌ ${endpoint} failed`);
    }
  };

  const sendPrompt = async () => {
    appendRight(`🧠 ${input}`);
    try {
      const res = await fetch('/api/aion', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: input }),
      });
      const data = await res.json();
      appendRight(`💬 ${data.response}`);
    } catch (e) {
      appendRight('❌ Prompt failed');
    }
    setInput('');
  };

  return (
    <div className={styles.container}>
      <Split className={styles.split} minSize={200} gutterSize={10}>
        <div className={styles.leftPane}>
          <div className={styles.visualizer}>
            <h2 className="font-semibold text-lg">🧠 Dream Visualizer</h2>
            <div className="p-4 bg-gray-100 rounded">Coming soon: Visualized dreams & memory maps</div>
          </div>
          <div className={styles.logBox}>
            {leftLogs.map((log, i) => (
              <div key={i} className={styles.logLine}>{log}</div>
            ))}
          </div>
        </div>

        <div className={styles.rightPane}>
          <div className={styles.logBox}>
            {rightLogs.map((log, i) => (
              <div key={i} className={styles.logLine}>{log}</div>
            ))}
          </div>
        </div>
      </Split>

      <div className={styles.footer}>
        <div className={styles.footerLeft}>
          <Button className="bg-purple-600" onClick={() => runEndpoint('boot-skill')}>🚀 Boot Skill</Button>
          <Button className="bg-yellow-500" onClick={() => runEndpoint('skill-reflect')}>✨ Reflect</Button>
          <Button className="bg-green-600" onClick={() => runEndpoint('run-dream')}>🌙 Run Dream</Button>
          <Button className="bg-indigo-600" onClick={() => runEndpoint('game-dream')}>🎮 Game Dream</Button>
        </div>
        <div className={styles.footerRight}>
          <input
            type="text"
            className={styles.inputBar}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask AION something..."
          />
          <Button className="ml-2 bg-black text-white" onClick={sendPrompt}>Ask</Button>
        </div>
      </div>
    </div>
  );
}