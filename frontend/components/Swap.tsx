// frontend/components/Swap.tsx
import React, { useState, useEffect } from "react";
import styles from "./Swap.module.css";

export default function SwapPanel() {
  const [sellAmt, setSellAmt] = useState("");
  const [buyAmt, setBuyAmt] = useState("");

  // dummy rate: 1 USDT → 0.95 GLU
  useEffect(() => {
    const a = parseFloat(sellAmt);
    setBuyAmt(!isNaN(a) ? (a * 0.95).toFixed(2) : "");
  }, [sellAmt]);

  return (
    <div className={styles.swapContainer}>
      <div className={styles.swapInner}>
        {/* Sell input */}
        <div className={styles.valueWrapper}>
          <input
            className={styles.swapValue}
            placeholder="0"
            value={sellAmt}
            onChange={(e) => setSellAmt(e.target.value)}
          />
          <button className={styles.tokenButton}>
            <img src="/icons/usdt.svg" alt="USDT" />
            USDT <span>▾</span>
          </button>
        </div>

        {/* Arrow */}
        <div className={styles.swapDivider} aria-label="Swap">
          ↓
        </div>

        {/* Buy input */}
        <div className={styles.valueWrapper}>
          <input
            className={styles.swapValue}
            placeholder="0"
            value={buyAmt}
            readOnly
          />
          <button className={styles.tokenButton}>
            <img src="/icons/glu.svg" alt="$GLU" />
            $GLU <span>▾</span>
          </button>
        </div>

        {/* Swap button */}
        <button className={styles.swapAction}>Swap</button>
      </div>
    </div>
  );
}

