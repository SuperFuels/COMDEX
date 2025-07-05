// components/AIONTerminal.tsx

import React, { useState } from 'react';
import styles from '@/styles/AIONDashboard.module.css';

interface AIONTerminalProps {
  side: 'left' | 'right';
}

export default function AIONTerminal({ side }: AIONTerminalProps) {
  const [input, setInput] = useState('');
  const [output, setOutput] = useState(side === 'left' ? 'Awaiting command...' : 'Ask me something...');
  const [loading, setLoading] = useState(false);

  const sendCommand = async (prompt: string) => {
    if (!prompt.trim()) return;
    setLoading(true);
    setOutput(`Sending command: ${prompt}`);
    try {
      const res = await fetch('/api/aion', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt }),
      });
      const data = await res.json();
      const result = data?.response || 'No response from AION.';
      setOutput(result);
    } catch (error) {
      setOutput('Error communicating with AION.');
    } finally {
      setLoading(false);
    }
  };

  const handleAsk = () => {
    sendCommand(input);
    setInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleAsk();
  };

  const presets = [
    { label: 'Status', cmd: 'Show current status' },
    { label: 'Goal', cmd: 'What is your current goal?' },
    { label: 'Identity', cmd: 'Who are you?' },
    { label: 'Situation', cmd: 'What is your situation?' },
    { label: 'Boot Skill', cmd: 'Load next boot skill' },
    { label: 'Reflect', cmd: 'Reflect on your recent activity' },
    { label: 'Run Dream', cmd: 'Generate a dream' },
  ];

  return (
    <div className={styles.terminalContainer}>
      <pre className={styles.terminalText}>{output}</pre>
      {side === 'right' && (
        <div className={styles.footerTerminal}>
          <div className={styles.presetButtons}>
            {presets.map(({ label, cmd }) => (
              <button
                key={label}
                className={styles.footerButton}
                onClick={() => sendCommand(cmd)}
                disabled={loading}
              >
                {label}
              </button>
            ))}
          </div>
          <div className={styles.promptRow}>
            <input
              className={styles.promptInput}
              placeholder="Ask AION something..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={loading}
            />
            <button
              className={styles.askButton}
              onClick={handleAsk}
              disabled={loading}
            >
              Ask
            </button>
          </div>
        </div>
      )}
    </div>
  );
}