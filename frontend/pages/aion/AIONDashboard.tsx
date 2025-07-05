import React, { useState } from 'react';
import dynamic from 'next/dynamic';
import styles from '@/styles/AIONDashboard.module.css';
import { Button } from '@/components/ui/button';

const AIONTerminal = dynamic(() => import('@/components/AIONTerminal'), { ssr: false });

export default function AIONDashboard() {
  const [leftOutput, setLeftOutput] = useState('');
  const [rightOutput, setRightOutput] = useState('');

  const handleButtonClick = async (endpoint: string) => {
    try {
      const res = await fetch(`/api/aion/${endpoint}`);
      const data = await res.json();
      setLeftOutput((prev) => `${prev}\n> /${endpoint}\n${JSON.stringify(data, null, 2)}`);
    } catch (err) {
      setLeftOutput((prev) => `${prev}\n> /${endpoint}\n[ERROR] ${err}`);
    }
  };

  const handleAsk = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const input = e.currentTarget.ask.value;
    if (!input) return;
    setRightOutput((prev) => `${prev}\n> ${input}`);
    e.currentTarget.reset();

    try {
      const res = await fetch('/api/aion', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: input }),
      });
      const data = await res.json();
      setRightOutput((prev) => `${prev}\n${data.response}`);
    } catch (err) {
      setRightOutput((prev) => `${prev}\n[ERROR] ${err}`);
    }
  };

  return (
    <div className={styles.dashboardContainer}>
      {/* Top Bar */}
      <div className={styles.topBar}>
        <h2 className={styles.heading}>🧠 Dream Visualizer</h2>
        <div className={styles.subtitle}>Coming soon: Visualized dreams & memory maps</div>
      </div>

      {/* Split Terminal Panels */}
      <div className={styles.terminalSection}>
        <div className={styles.terminalPanel}>
          <pre className={styles.terminalText}>{leftOutput || 'Awaiting command...'}</pre>
        </div>
        <div className={styles.divider}></div>
        <div className={styles.terminalPanel}>
          <pre className={styles.terminalText}>{rightOutput || 'Ask me something...'}</pre>
        </div>
      </div>

      {/* Sticky Footer Terminal Controls */}
      <div className={styles.footerTerminal}>
        <div className={styles.footerLeft}>
          <Button onClick={() => handleButtonClick('identity')}>Identity</Button>
          <Button onClick={() => handleButtonClick('goal')}>Goal</Button>
          <Button onClick={() => handleButtonClick('situation')}>Situation</Button>
          <Button onClick={() => handleButtonClick('boot-skill')}>Boot Skill</Button>
          <Button onClick={() => handleButtonClick('skill-reflect')}>Skill Reflect</Button>
          <Button onClick={() => handleButtonClick('run-dream')}>Run Dream</Button>
        </div>
        <div className={styles.footerRight}>
          <form onSubmit={handleAsk} className={styles.askForm}>
            <input
              type="text"
              name="ask"
              placeholder="Ask AION anything..."
              className={styles.askInput}
            />
            <Button type="submit">Send</Button>
          </form>
        </div>
      </div>

      {/* Hidden Terminal Engine (mounts real-time terminal) */}
      <AIONTerminal />
    </div>
  );
}