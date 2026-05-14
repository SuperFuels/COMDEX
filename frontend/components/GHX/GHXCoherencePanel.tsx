// frontend/components/GHX/GHXCoherencePanel.tsx
'use client';
import React, { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface CoherenceFrame {
  t: number;
  phi: number;
  coherence: number;
}

export default function GHXCoherencePanel() {
  const [frames, setFrames] = useState<CoherenceFrame[]>([]);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const bufferRef = useRef<CoherenceFrame[]>([]);

  // 🔁 Mock or Live Stream
useEffect(() => {
  // 👇 Force browser-compatible interval type
  let interval: number;
  let phi = 0;

  interval = window.setInterval(() => {
    phi += 0.05;
    const coherence = 0.5 + 0.5 * Math.sin(phi / 2);
    const frame: CoherenceFrame = { t: Date.now(), phi, coherence };
    bufferRef.current = [...bufferRef.current.slice(-60), frame];
    setFrames([...bufferRef.current]);
  }, 300);

  return () => window.clearInterval(interval);
}, []);

  // 🌈 Color mapping by coherence
  const current = frames[frames.length - 1];
  const hue = current ? 120 * current.coherence : 0; // green→red
  const color = `hsl(${hue}, 90%, 55%)`;

  // 🎵 Pulse scaling
  const scale = 0.9 + (current ? current.coherence * 0.4 : 0.9);

  return (
    <div className="fixed bottom-4 right-4 z-50 text-center text-white select-none">
      <AnimatePresence>
        {!isCollapsed && (
          <motion.div
            key="panel"
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 40 }}
            transition={{ duration: 0.4 }}
            className="relative w-40 h-40 rounded-full border border-white/10 shadow-2xl overflow-hidden bg-black/60 backdrop-blur-lg"
          >
            <motion.div
              className="absolute inset-0 rounded-full"
              animate={{ scale, backgroundColor: color }}
              transition={{ type: 'spring', stiffness: 100, damping: 20 }}
            />
            <div className="absolute inset-0 flex flex-col items-center justify-center font-mono">
              <div className="text-lg">Φ</div>
              <div className="text-2xl font-bold">
                {(current?.phi ?? 0).toFixed(3)}
              </div>
              <div className="text-xs opacity-80">
                coherence: {(current?.coherence ?? 0).toFixed(3)}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
      <button
        onClick={() => setIsCollapsed((v) => !v)}
        className="mt-2 px-3 py-1 text-xs border border-white/20 rounded-lg bg-black/40 hover:bg-black/60 transition"
      >
        {isCollapsed ? '🌌 Show GHX' : '🛑 Collapse GHX'}
      </button>
    </div>
  );
}