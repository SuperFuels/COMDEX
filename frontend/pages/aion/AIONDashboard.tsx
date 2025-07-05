// pages/aion/AIONDashboard.tsx
import React from 'react';
import dynamic from 'next/dynamic';
import styles from '@/styles/AIONDashboard.module.css';

const AIONTerminal = dynamic(() => import('@/components/AIONTerminal'), { ssr: false });

export default function AIONDashboard() {
  return (
    <div className={styles.dashboardWrapper}>
      <div className={styles.splitContainer}>
        <div className={styles.leftPanel}>
          <AIONTerminal side="left" />
        </div>
        <div className={styles.divider} />
        <div className={styles.rightPanel}>
          <AIONTerminal side="right" />
        </div>
      </div>
      <div className={styles.footerSticky}>
        <p className={styles.footerText}>Dream Visualizer (Coming Soon)</p>
      </div>
    </div>
  );
}