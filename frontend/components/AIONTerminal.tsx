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
      setOutput(data?.response || 'No response from AION.');
    } catch (e) {
      setOutput('Error communicating with AION.');
    } finally {
      setLoading(false);
    }
  };

  const handleAsk = () => {
    sendCommand(input);
    setInput('');
  };

  return (
    <div className={styles.terminalWrapper}>
      <div className={styles.terminalOutput}>{output}</div>
      <div className={styles.terminalControls}>
        <input
          className={styles.promptInput}
          value={input}
          placeholder="Type your command..."
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleAsk()}
        />
        <button onClick={handleAsk} className={styles.askButton} disabled={loading}>
          Ask
        </button>
      </div>
    </div>
  );
}