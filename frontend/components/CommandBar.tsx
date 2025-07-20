// components/CommandBar.tsx

import React, { useState, useEffect } from 'react';
import {
  ChevronDown,
  Star,
  Clock,
  CheckCircle,
  XCircle,
  Loader,
  Terminal,
  Zap,
  Brain,
  FileText,
  Eye,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { saveAs } from 'file-saver';
import toast from 'react-hot-toast';

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

type Suggestion = {
  text: string;
  type?: 'system' | 'boot' | 'glyph' | 'data' | 'user';
  description?: string;
};

export default function CommandBar({
  input,
  setInput,
  loading,
  onSubmit,
  presets,
  setInputFromPreset,
}: CommandBarProps) {
  const [showDropdown, setShowDropdown] = useState(false);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [history, setHistory] = useState<string[]>([]);
  const [favorites, setFavorites] = useState<string[]>([]);
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [filter, setFilter] = useState<'all' | 'system' | 'boot' | 'glyph' | 'data'>('all');

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

  const handleSubmit = async () => {
    if (!input.trim()) return;

    // Special command: bundle_container <id>
    if (input.startsWith("bundle_container")) {
      const containerId = input.split(" ")[1];
      if (!containerId) {
        toast.error("Missing container ID");
        return;
      }

      try {
        const res = await fetch(`/api/aion/bundle/${containerId}`);
        const data = await res.json();

        if (data.status === "success" && data.bundle) {
          const filename = `AION_${containerId}_${Date.now()}.lux`;
          const blob = new Blob([data.bundle], { type: "text/plain" });
          saveAs(blob, filename);
          toast.success(`🧠 Saved ${filename}`);

          // Trigger WebSocket event or feedback if needed
          const protocol = window.location.protocol === "https:" ? "wss" : "ws";
          const ws = new WebSocket(`${protocol}://${window.location.host}/ws/containers`);
          ws.onopen = () => {
            ws.send(JSON.stringify({ event: 'bundle_trigger', id: containerId }));
            ws.close();
          };
        } else {
          toast.error(`❌ ${data.error || "Bundle failed"}`);
        }
      } catch (err) {
        toast.error("❌ Request failed");
        console.error(err);
      }

      return;
    }

    const newHistory = [input, ...history.filter((h) => h !== input)].slice(0, MAX_HISTORY);
    setHistory(newHistory);
    localStorage.setItem(HISTORY_KEY, JSON.stringify(newHistory));
    setSuggestions([]);
    setStatus('loading');

    try {
      await onSubmit();
      setStatus('success');
    } catch {
      setStatus('error');
    } finally {
      setTimeout(() => setStatus('idle'), 2500);
    }
  };

  const toggleFavorite = (cmd: string) => {
    const updated = favorites.includes(cmd)
      ? favorites.filter((f) => f !== cmd)
      : [...favorites, cmd];
    setFavorites(updated);
    localStorage.setItem(FAVORITES_KEY, JSON.stringify(updated));
  };

  const handleSuggestionClick = (value: string) => {
    setInput(value);
    setSuggestions([]);
  };

  const iconForType = (type: string | undefined) => {
    switch (type) {
      case 'system':
        return <Terminal size={14} className="text-gray-500 mr-1" />;
      case 'boot':
        return <Zap size={14} className="text-blue-500 mr-1" />;
      case 'glyph':
        return <Brain size={14} className="text-purple-500 mr-1" />;
      case 'data':
        return <FileText size={14} className="text-green-500 mr-1" />;
      default:
        return <Eye size={14} className="text-gray-400 mr-1" />;
    }
  };

  const filteredSuggestions = suggestions.filter(
    (s) => filter === 'all' || s.type === filter
  );

  return (
    <div className="relative w-full flex flex-col gap-3">
      {/* Input Row */}
      <div className="flex items-center gap-2">
        <div className="flex-grow relative">
          <input
            type="text"
            className="w-full p-2 border border-gray-300 rounded-md focus:outline-none pr-10"
            placeholder="Run command or select preset..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
          />
          <button
            className="absolute top-2 right-2 text-gray-500 hover:text-gray-800"
            onClick={() => setShowDropdown(!showDropdown)}
          >
            <ChevronDown size={16} />
          </button>

          {/* Preset Commands Dropdown */}
          {showDropdown && (
            <div className="absolute z-30 w-full mt-1 bg-white border border-gray-300 rounded shadow-md max-h-60 overflow-y-auto">
              {presets.map((preset, idx) => (
                <div
                  key={idx}
                  className="px-3 py-2 cursor-pointer hover:bg-gray-100 text-sm"
                  onClick={() => {
                    setInputFromPreset(preset);
                    setShowDropdown(false);
                    setTimeout(() => onSubmit(), 100);
                  }}
                >
                  {preset}
                </div>
              ))}
            </div>
          )}

          {/* Suggestion Dropdown */}
          {filteredSuggestions.length > 0 && (
            <div className="absolute z-20 w-full mt-1 bg-white border border-blue-400 rounded shadow-md max-h-60 overflow-y-auto">
              {filteredSuggestions.map((sug, idx) => (
                <div
                  key={idx}
                  className="px-3 py-2 text-sm flex items-start gap-2 hover:bg-blue-100 cursor-pointer"
                  onClick={() => handleSuggestionClick(sug.text)}
                >
                  {iconForType(sug.type)}
                  <div>
                    <div>{sug.text}</div>
                    {sug.description && (
                      <div className="text-xs text-gray-500">{sug.description}</div>
                    )}
                  </div>
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

        <div className="w-5">
          {status === 'loading' && <Loader className="animate-spin text-gray-400" size={20} />}
          {status === 'success' && <CheckCircle className="text-green-500" size={20} />}
          {status === 'error' && <XCircle className="text-red-500" size={20} />}
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex space-x-3 text-xs text-gray-600 ml-1">
        {['all', 'system', 'boot', 'glyph', 'data'].map((cat) => (
          <button
            key={cat}
            onClick={() => setFilter(cat as any)}
            className={cn(
              'px-2 py-1 rounded',
              filter === cat ? 'bg-blue-100 text-blue-600 font-medium' : 'hover:bg-gray-100'
            )}
          >
            {cat.toUpperCase()}
          </button>
        ))}
      </div>

      {/* History & Favorites */}
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