'use client';

import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';

interface CreativeStep {
  step: number;
  glyph: string;
  mutation: string;
}

export default function CreativeReplay() {
  const [trace, setTrace] = useState<CreativeStep[]>([]);
  const [tick, setTick] = useState(0);
  const [playing, setPlaying] = useState(true);

  useEffect(() => {
    fetch('/containers/creativecore_trace_test.dc.json')
      .then((res) => res.json())
      .then((data) => {
        setTrace(data.creativeTrace || []);
      });
  }, []);

  useEffect(() => {
    if (playing && trace.length > 0) {
      const interval = setInterval(() => {
        setTick((prev) => (prev + 1) % trace.length);
      }, 1500);
      return () => clearInterval(interval);
    }
  }, [playing, trace]);

  if (trace.length === 0) {
    return <div className="text-white p-4">🧠 Loading creative replay...</div>;
  }

  const current = trace[tick];

  return (
    <div className="w-full h-screen bg-black flex flex-col items-center justify-center">
      <div className="text-white text-3xl mb-2">CreativeCore Replay</div>
      <div className="text-gray-400 mb-6">Step {current.step + 1} / {trace.length}</div>

      <motion.div
        key={tick}
        initial={{ opacity: 0, y: 10, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.6 }}
        className="bg-gray-800 border border-white text-white px-6 py-4 rounded-xl shadow-xl w-[400px] text-center"
      >
        <div className="text-xl font-bold text-cyan-300">{current.glyph}</div>
        <div className="text-lg mt-2 text-yellow-300">{current.mutation}</div>
      </motion.div>

      <div className="mt-6 flex gap-4">
        <button
          onClick={() => setPlaying((p) => !p)}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded"
        >
          {playing ? '⏸ Pause' : '▶️ Play'}
        </button>
        <button
          onClick={() => setTick((tick + 1) % trace.length)}
          className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded"
        >
          ⏭ Next Step
        </button>
      </div>
    </div>
  );
}