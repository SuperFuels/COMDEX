// frontend/components/runtime_player.tsx
import React, { useEffect, useState, useRef } from 'react';
import TimelineControls from './AION/TimelineControls';

interface RuntimePlayerProps {
  totalTicks: number;
  currentTick: number;
  onTickChange: (tick: number) => void;
  tickInterval?: number; // in ms
}

const RuntimePlayer: React.FC<RuntimePlayerProps> = ({
  totalTicks,
  currentTick,
  onTickChange,
  tickInterval = 1000,
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const [scrubTick, setScrubTick] = useState(currentTick);

  useEffect(() => {
    setScrubTick(currentTick);
  }, [currentTick]);

  useEffect(() => {
    if (isPlaying) {
      intervalRef.current = setInterval(() => {
        onTickChange((prev) => {
          const next = prev + 1;
          if (next >= totalTicks) {
            clearInterval(intervalRef.current!);
            setIsPlaying(false);
            return prev;
          }
          return next;
        });
      }, tickInterval);
    } else if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [isPlaying, tickInterval, totalTicks]);

  const handlePlay = () => setIsPlaying(true);
  const handlePause = () => setIsPlaying(false);
  const handlePrev = () => onTickChange(Math.max(0, currentTick - 1));
  const handleNext = () => onTickChange(Math.min(totalTicks - 1, currentTick + 1));

  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newTick = parseInt(e.target.value, 10);
    setScrubTick(newTick);
    onTickChange(newTick);
  };

  return (
    <div className="w-full p-2 bg-gray-50 border rounded-md shadow-sm">
      <TimelineControls
        onPlay={handlePlay}
        onPause={handlePause}
        onPrev={handlePrev}
        onNext={handleNext}
        isPlaying={isPlaying}
        currentTick={currentTick}
      />
      <input
        type="range"
        min={0}
        max={totalTicks - 1}
        value={scrubTick}
        onChange={handleSliderChange}
        className="w-full mt-2"
      />
    </div>
  );
};

export default RuntimePlayer;
