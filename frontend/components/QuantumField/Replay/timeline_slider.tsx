'use client';

import React, { useEffect, useState } from 'react';
import { PlayIcon, PauseIcon, RewindIcon } from 'lucide-react';

interface TimelineSliderProps {
  maxTick: number;
  currentTick: number;
  onTickChange: (tick: number) => void;
  autoPlay?: boolean;
  /** ms per tick */
  speed?: number;
}

const TimelineSlider: React.FC<TimelineSliderProps> = ({
  maxTick,
  currentTick,
  onTickChange,
  autoPlay = false,
  speed = 1000,
}) => {
  const [tick, setTick] = useState<number>(currentTick ?? 0);
  const [playing, setPlaying] = useState<boolean>(autoPlay);

  // keep internal state in sync with parent
  useEffect(() => {
    setTick(Math.min(currentTick ?? 0, maxTick));
  }, [currentTick, maxTick]);

  // clamp if maxTick shrinks
  useEffect(() => {
    if (tick > maxTick) {
      setTick(maxTick);
      onTickChange(maxTick);
    }
  }, [maxTick]); // eslint-disable-line react-hooks/exhaustive-deps

  // autoplay loop
  useEffect(() => {
    if (!playing) return;
    const id = setInterval(() => {
      setTick(prev => {
        const next = prev + 1;
        if (next > maxTick) {
          setPlaying(false);
          return prev;
        }
        onTickChange(next);
        return next;
      });
    }, speed);
    return () => clearInterval(id);
  }, [playing, maxTick, speed, onTickChange]);

  const handleRangeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newTick = Number(e.target.value);
    setTick(newTick);
    onTickChange(newTick);
    setPlaying(false); // pause when user scrubs
  };

  return (
    <div className="w-full px-4 py-2 bg-black/70 rounded-md text-white text-xs flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <div className="flex gap-2 items-center">
          <button
            onClick={() => {
              setTick(0);
              onTickChange(0);
              setPlaying(false);
            }}
            title="Rewind"
            className="p-1 rounded hover:bg-white/10"
          >
            <RewindIcon className="w-4 h-4" />
          </button>

          <button
            onClick={() => setPlaying(p => !p)}
            title={playing ? 'Pause' : 'Play'}
            className="p-1 rounded hover:bg-white/10"
          >
            {playing ? <PauseIcon className="w-4 h-4" /> : <PlayIcon className="w-4 h-4" />}
          </button>
        </div>

        <div>
          Tick: <strong>{tick}</strong> / {maxTick}
        </div>
      </div>

      {/* Native range slider (no external UI dep) */}
      <input
        type="range"
        min={0}
        max={maxTick}
        step={1}
        value={tick}
        onChange={handleRangeChange}
        className="w-full accent-cyan-400"
        aria-label="Timeline tick"
      />
    </div>
  );
};

export default TimelineSlider;