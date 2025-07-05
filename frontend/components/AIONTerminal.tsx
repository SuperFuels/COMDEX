// components/AIONTerminal.tsx
import React, { useState } from 'react';
import styles from '@/styles/AIONDashboard.module.css';

interface AIONTerminalProps {
  side: 'left' | 'right';
  endpoint?: string;
}

export default function AIONTerminal({ side, endpoint = '/api/aion' }: AIONTerminalProps) {
  const [input, setInput] = useState('');
  const [output, setOutput] = useState(side === 'left' ? 'Awaiting command...' : 'Ask me something...');
  const [loading, setLoading] = useState(false);

  const sendCommand = async (prompt: string) => {
    if (!prompt.trim()) return;
    setLoading(true);
    setOutput(`Sending command: ${prompt}`);
    try {
      const res = await fetch(endpoint, {
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

  return (
    <div className={styles.terminalWrapper}>
      <div className={styles.terminalOutput}>{output}</div>
    </div>
  );
}