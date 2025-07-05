import React, { useState, useEffect } from 'react';
import { ChevronDown, Star, Clock } from 'lucide-react';
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

const HISTORY_KEY = 'aion_history';
const FAVORITES_KEY = 'aion_favorites';
const MAX_HISTORY = 10;

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
  const [history, setHistory] = useState<string[]>([]);
  const [favorites, setFavorites] = useState<string[]>([]);

  useEffect(() => {
    const storedHistory = JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]');
    const storedFavorites = JSON.parse(localStorage.getItem(FAVORITES_KEY) || '[]');
    setHistory(storedHistory);
    setFavorites(storedFavorites);
  }, []);

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

  const handleSubmit = () => {
    if (!input.trim()) return;
    const newHistory = [input, ...history.filter((h) => h !== input)].slice(0, MAX_HISTORY);
    setHistory(newHistory);
    localStorage.setItem(HISTORY_KEY, JSON.stringify(newHistory));
    setSuggestions([]);
    onSubmit();
  };

  const toggleFavorite = (cmd: string) => {
    let updated;
    if (favorites.includes(cmd)) {
      updated = favorites.filter((f) => f !== cmd);
    } else {
      updated = [...favorites, cmd];
    }
    setFavorites(updated);
    localStorage.setItem(FAVORITES_KEY, JSON.stringify(updated));
  };

  const handleSuggestionClick = (value: string) => {
    setInput(value);
    setSuggestions([]);
  };

  return (
    <div className="relative w-full flex flex-col gap-3">
      {/* Input & Dropdown */}
      <div className="flex items-center gap-2">
        <div className="flex-grow relative">
          <input
            type="text"
            className="w-full p-2 border border-gray-300 rounded-md focus:outline-none pr-10"
            placeholder="Run command or select preset..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleSubmit();
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
          onClick={handleSubmit}
          disabled={loading || !input.trim()}
          className={cn(
            'bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md transition',
            loading && 'opacity-50 cursor-not-allowed'
          )}
        >
          Run
        </Button>
      </div>

      {/* History & Favorites Section */}
      {(favorites.length > 0 || history.length > 0) && (
        <div className="flex flex-wrap gap-2 text-xs text-gray-700">
          {[...favorites, ...history.filter((h) => !favorites.includes(h))].map((cmd, idx) => (
            <div
              key={idx}
              className="flex items-center bg-gray-100 px-2 py-1 rounded cursor-pointer hover:bg-gray-200"
              onClick={() => setInput(cmd)}
            >
              {favorites.includes(cmd) ? (
                <Star
                  size={14}
                  className="text-yellow-500 mr-1"
                  onClick={(e) => {
                    e.stopPropagation();
                    toggleFavorite(cmd);
                  }}
                />
              ) : (
                <Clock
                  size={14}
                  className="text-gray-400 mr-1"
                  onClick={(e) => {
                    e.stopPropagation();
                    toggleFavorite(cmd);
                  }}
                />
              )}
              {cmd}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}