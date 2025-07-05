import React, { useRef, useState } from 'react';
import AIONTerminal from '@/components/AIONTerminal';

export default function Dashboard() {
  const [leftWidth, setLeftWidth] = useState(50);
  const containerRef = useRef<HTMLDivElement>(null);
  const isDragging = useRef(false);

  const startDrag = () => (isDragging.current = true);
  const stopDrag = () => (isDragging.current = false);

  const handleDrag = (e: React.MouseEvent) => {
    if (!isDragging.current || !containerRef.current) return;
    const containerWidth = containerRef.current.offsetWidth;
    const newLeftWidth = (e.clientX / containerWidth) * 100;
    if (newLeftWidth > 10 && newLeftWidth < 90) {
      setLeftWidth(newLeftWidth);
    }
  };

  return (
    <div className={styles.dashboardContainer} ref={containerRef} onMouseMove={handleDrag} onMouseUp={stopDrag}>
      <div className={styles.panel} style={{ width: `${leftWidth}%` }}>
        <AIONTerminal side="left" />
      </div>
      <div
        className={styles.divider}
        onMouseDown={startDrag}
        onMouseUp={stopDrag}
      />
      <div className={styles.panel} style={{ width: `${100 - leftWidth}%` }}>
        <AIONTerminal side="right" />
      </div>

      <footer className={styles.footer}>
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
          />
          <button className={styles.askButton}>Ask</button>
        </div>
      </footer>
    </div>
  );
}