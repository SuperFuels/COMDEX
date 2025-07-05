import React, { useState, useEffect } from 'react';
import styles from '@/styles/AIONTerminal.module.css';

export default function AIONTerminal() {
  const [input, setInput] = useState('');
  const [response, setResponse] = useState('');
  const [commandLog, setCommandLog] = useState([]);
  const [leftOutput, setLeftOutput] = useState('Awaiting command...');
  const [rightOutput, setRightOutput] = useState('Ask me something...');

  const handleAsk = async () => {
    if (!input.trim()) return;
    setCommandLog((prev) => [...prev, `> ${input}`]);
    setLeftOutput(`Sending command: ${input}`);
    try {
      const res = await fetch('/api/aion', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: input }),
      });
      const data = await res.json();
      const output = data?.response || 'No response from AION.';
      setRightOutput(output);
      setResponse(output);
      setCommandLog((prev) => [...prev, output]);
    } catch (err) {
      setRightOutput('Error communicating with AION.');
    }
    setInput('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') handleAsk();
  };

  const presetButtons = [
    { label: 'Status', cmd: 'Show current status' },
    { label: 'Goal', cmd: 'What is your current goal?' },
    { label: 'Identity', cmd: 'Who are you?' },
    { label: 'Situation', cmd: 'What is your situation?' },
    { label: 'Boot Skill', cmd: 'Load next boot skill' },
    { label: 'Reflect', cmd: 'Reflect on your recent activity' },
    { label: 'Run Dream', cmd: 'Generate a dream' },
  ];

  return (
    <div className={styles.terminalWrapper}>
      <div className={styles.leftTerminal}>
        <pre className={styles.terminalText}>{leftOutput}</pre>
      </div>
      <div className={styles.rightTerminal}>
        <pre className={styles.terminalText}>{rightOutput}</pre>
      </div>
      <div className={styles.footerTerminal}>
        <div className={styles.presetButtons}>
          {presetButtons.map(({ label, cmd }) => (
            <button
              key={label}
              onClick={() => {
                setInput(cmd);
                setTimeout(() => handleAsk(), 100);
              }}
              className={styles.footerButton}
            >
              {label}
            </button>
          ))}
        </div>
        <input
          className={styles.promptInput}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask AION something..."
        />
        <button onClick={handleAsk} className={styles.askButton}>
          Ask
        </button>
      </div>
    </div>
  );
}