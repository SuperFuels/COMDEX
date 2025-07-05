// File: frontend/pages/aion/AIONDashboard.tsx
import React from 'react';
import dynamic from 'next/dynamic';
import styles from '@/styles/AIONDashboard.module.css';

const AIONTerminal = dynamic(() => import('@/components/AIONTerminal'), { ssr: false });

export default function AIONDashboard() {
  return (
    <div className={styles.dashboardContainer}>
      <div className={styles.mainContent}>
        {/* Left side with Dream Visualizer and Endpoint Output */}
        <div className={styles.leftPanel}>
          <div className={styles.visualizerSection}>
            <h2 className={styles.heading}>🧠 Dream Visualizer</h2>
            <div className={styles.subtitle}>Coming soon: Visualized dreams & memory maps</div>
          </div>
          <div id="aion-left-terminal" className={styles.terminalPanel}>
            <p className={styles.terminalText}>Awaiting command...</p>
          </div>
        </div>

        {/* Divider */}
        <div className={styles.divider} />

        {/* Right terminal panel */}
        <div id="aion-right-terminal" className={styles.terminalPanel}>
          <p className={styles.terminalText}>Ask me something...</p>
        </div>
      </div>

      {/* Sticky Footer Terminal */}
      <div className={styles.footerTerminal}>
        <AIONTerminal />
      </div>
    </div>
  );
}