import React, { useState, useEffect } from "react";
import { Slider } from "@/components/ui/slider";
import { PlayIcon, PauseIcon, RewindIcon } from "lucide-react";

interface TimelineSliderProps {
  maxTick: number;
  currentTick: number;
  onTickChange: (tick: number) => void;
  autoPlay?: boolean;
  speed?: number; // ms per tick
}

const TimelineSlider: React.FC<TimelineSliderProps> = ({
  maxTick,
  currentTick,
  onTickChange,
  autoPlay = false,
  speed = 1000,
}) => {
  const [tick, setTick] = useState(currentTick);
  const [playing, setPlaying] = useState(autoPlay);

  useEffect(() => {
    setTick(currentTick);
  }, [currentTick]);

  useEffect(() => {
    if (!playing) return;
    const interval = setInterval(() => {
      setTick((prev) => {
        const next = prev + 1;
        if (next > maxTick) {
          setPlaying(false);
          return prev;
        }
        onTickChange(next);
        return next;
      });
    }, speed);
    return () => clearInterval(interval);
  }, [playing, maxTick, speed, onTickChange]);

  const handleSliderChange = (val: number[]) => {
    const newTick = val[0];
    setTick(newTick);
    onTickChange(newTick);
    setPlaying(false); // pause autoplay when user manually changes
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
          >
            <RewindIcon className="w-4 h-4" />
          </button>

          <button
            onClick={() => setPlaying((p) => !p)}
            title={playing ? "Pause" : "Play"}
          >
            {playing ? (
              <PauseIcon className="w-4 h-4" />
            ) : (
              <PlayIcon className="w-4 h-4" />
            )}
          </button>
        </div>
        <div>
          Tick: <strong>{tick}</strong> / {maxTick}
        </div>
      </div>
      <Slider
        min={0}
        max={maxTick}
        step={1}
        value={[tick]}
        onValueChange={handleSliderChange}
        className="w-full"
      />
    </div>
  );
};

export default TimelineSlider;