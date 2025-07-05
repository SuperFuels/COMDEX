import React, { useState } from 'react';
import styles from '@/styles/AIONDashboard.module.css';

interface AIONTerminalProps {
  side: 'left' | 'right';
}

export default function AIONTerminal({ side }: AIONTerminalProps) {
  const [output, setOutput] = useState(
    side === 'left' ? 'Awaiting command...' : 'No response from AION.'
  );
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

  // Footer ask handler if wired externally
  React.useEffect(() => {
    if (side === 'right') {
      const askBtn = document.getElementById('aion-footer-ask');
      const inputBox = document.getElementById('aion-footer-input') as HTMLInputElement;
      if (askBtn && inputBox) {
        askBtn.onclick = () => {
          const prompt = inputBox.value;
          inputBox.value = '';
          sendCommand(prompt);
        };
        inputBox.onkeydown = (e: KeyboardEvent) => {
          if (e.key === 'Enter') {
            askBtn.click();
          }
        };
      }
    }
  }, [side]);

  return (
    <div className={styles.terminalWrapper}>
      <div className={styles.terminalOutput}>{loading ? 'Loading...' : output}</div>
    </div>
  );
}