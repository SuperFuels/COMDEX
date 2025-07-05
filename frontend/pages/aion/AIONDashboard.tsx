import React from 'react';
import AIONTerminal from '@/components/AIONTerminal';
import styles from '@/styles/AIONDashboard.module.css';

export default function AIONDashboard() {
  return (
    <div className={styles.dashboardWrapper}>
      <div className={styles.splitScreen}>
        <div className={styles.leftPane}>
          <AIONTerminal side="left" />
        </div>
        <div className={styles.divider} />
        <div className={styles.rightPane}>
          <AIONTerminal side="right" />
        </div>
      </div>

      <div className={styles.footer}>
        <div className={styles.footerLeft}>
          <button className={styles.footerButton}>Status</button>
          <button className={styles.footerButton}>Goal</button>
          <button className={styles.footerButton}>Identity</button>
          <button className={styles.footerButton}>Situation</button>
          <span className={styles.footerLabel}>Dream Visualizer (Coming Soon)</span>
        </div>
        <div className={styles.footerRight}>
          <input
            className={styles.promptInput}
            placeholder="Type your command..."
            id="aion-footer-input"
          />
          <button className={styles.askButton} id="aion-footer-ask">Ask</button>
        </div>
      </div>
    </div>
  );
}