// components/AION/TimelineControls.tsx

import React from 'react';

interface TimelineControlsProps {
  onPlay: () => void;
  onPause: () => void;
  onPrev: () => void;
  onNext: () => void;
  isPlaying: boolean;
  currentTick: number;
}

const TimelineControls: React.FC<TimelineControlsProps> = ({
  onPlay,
  onPause,
  onPrev,
  onNext,
  isPlaying,
  currentTick,
}) => {
  return (
    <div className="flex gap-2 items-center text-xs text-gray-700 mt-2">
      <button
        onClick={onPrev}
        className="px-2 py-1 rounded bg-gray-100 border hover:bg-gray-200"
      >
        ⏪ Prev
      </button>
      {isPlaying ? (
        <button
          onClick={onPause}
          className="px-2 py-1 rounded bg-red-100 border hover:bg-red-200"
        >
          ⏸ Pause
        </button>
      ) : (
        <button
          onClick={onPlay}
          className="px-2 py-1 rounded bg-green-100 border hover:bg-green-200"
        >
          ▶️ Play
        </button>
      )}
      <button
        onClick={onNext}
        className="px-2 py-1 rounded bg-gray-100 border hover:bg-gray-200"
      >
        ⏩ Next
      </button>
      <span className="ml-4">Tick: {currentTick}</span>
    </div>
  );
};

export default TimelineControls;