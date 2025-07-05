import React, { useState, useEffect } from 'react';
import { ChevronDown } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface CommandBarProps {
  input: string;
  setInput: (value: string) => void;
  loading: boolean;
  onSubmit: () => void;
  presets: string[];
  setInputFromPreset: (value: string) => void;
}

export default function CommandBar({
  input,
  setInput,
  loading,
  onSubmit,
  presets,
  setInputFromPreset,
}: CommandBarProps) {
  const [showDropdown, setShowDropdown] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);

  useEffect(() => {
    const delayDebounce = setTimeout(() => {
      if (input.trim().length > 1) {
        fetch('/api/aion/suggest', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: input }),
        })
          .then((res) => res.json())
          .then((data) => setSuggestions(data.suggestions || []))
          .catch(() => setSuggestions([]));
      } else {
        setSuggestions([]);
      }
    }, 200);

    return () => clearTimeout(delayDebounce);
  }, [input]);

  const handleSuggestionClick = (value: string) => {
    setInput(value);
    setSuggestions([]);
  };

  return (
    <div className="relative w-full flex items-center gap-2">
      <div className="flex-grow relative">
        <input
          type="text"
          className="w-full p-2 border border-gray-300 rounded-md focus:outline-none pr-10"
          placeholder="Run command or select preset..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              onSubmit();
              setSuggestions([]);
            }
          }}
        />

        <button
          className="absolute top-2 right-2 text-gray-500 hover:text-gray-800"
          onClick={() => setShowDropdown(!showDropdown)}
        >
          <ChevronDown size={16} />
        </button>

        {/* Presets Dropdown */}
        {showDropdown && (
          <div className="absolute z-20 w-full mt-1 bg-white border border-gray-300 rounded shadow-md max-h-60 overflow-y-auto">
            {presets.map((preset, idx) => (
              <div
                key={idx}
                className="px-3 py-2 cursor-pointer hover:bg-gray-100 text-sm"
                onClick={() => {
                  setInputFromPreset(preset);
                  setShowDropdown(false);
                }}
              >
                {preset}
              </div>
            ))}
          </div>
        )}

        {/* Live Suggestions Dropdown */}
        {suggestions.length > 0 && (
          <div className="absolute z-10 w-full mt-1 bg-white border border-blue-400 rounded shadow-md max-h-60 overflow-y-auto">
            {suggestions.map((sug, idx) => (
              <div
                key={idx}
                className="px-3 py-2 cursor-pointer hover:bg-blue-100 text-sm"
                onClick={() => handleSuggestionClick(sug)}
              >
                {sug}
              </div>
            ))}
          </div>
        )}
      </div>

      <Button
        onClick={onSubmit}
        disabled={loading || !input.trim()}
        className={cn(
          'bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md transition',
          loading && 'opacity-50 cursor-not-allowed'
        )}
      >
        Run
      </Button>
    </div>
  );
}