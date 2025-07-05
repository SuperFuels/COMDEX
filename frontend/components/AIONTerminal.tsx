// AIONTerminal.tsx
import React, { useState, useEffect } from 'react';
import {
  FaPlay, FaBolt, FaCogs, FaBrain, FaBullseye, FaSync, FaChevronDown
} from 'react-icons/fa';
import useAION from '../hooks/useAION';

interface AIONTerminalProps {
  side: 'left' | 'right';
}

export default function AIONTerminal({ side }: AIONTerminalProps) {
  const {
    input,
    setInput,
    loading,
    messages,
    sendPrompt,
    callEndpoint,
    bottomRef,
  } = useAION();

  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [selectedLabel, setSelectedLabel] = useState('Select AION Preset');

  const presets = [
    { label: 'Run Full Learning Cycle', value: 'run-learning-cycle', icon: <FaPlay className="text-blue-600" /> },
    { label: 'Nightly Dream Trigger', value: 'run-dream', icon: <FaBolt className="text-yellow-500" /> },
    { label: 'Boot Next Skill', value: 'boot-skill', icon: <FaCogs className="text-gray-600" /> },
    { label: 'Reflect on Skills', value: 'skill-reflect', icon: <FaBrain className="text-purple-500" /> },
    { label: 'Check Goals', value: 'goal', icon: <FaBullseye className="text-green-600" /> },
    { label: 'System Status', value: 'status', icon: <FaSync className="text-indigo-600" /> },
  ];

  const runPreset = async (value: string, label: string) => {
    setDropdownOpen(false);
    setSelectedLabel(label);
    const method: 'get' | 'post' = value === 'goal' || value === 'status' ? 'get' : 'post';
    const url = `/api/aion/${value}`;
    await callEndpoint(url, label, method);
  };

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="flex flex-col h-full">
      {/* Left terminal only: show dropdown */}
      {side === 'left' && (
        <div className="relative px-2 py-1">
          <button
            onClick={() => setDropdownOpen(!dropdownOpen)}
            className="w-full border border-gray-300 rounded px-3 py-1 flex justify-between items-center text-sm bg-white hover:shadow"
          >
            <span>{selectedLabel}</span>
            <FaChevronDown className="ml-2 text-gray-400" />
          </button>
          {dropdownOpen && (
            <div className="absolute mt-1 w-full bg-white border border-gray-200 rounded shadow-lg z-10 max-h-60 overflow-auto">
              {presets.map((preset) => (
                <button
                  key={preset.value}
                  onClick={() => runPreset(preset.value, preset.label)}
                  className="flex items-center w-full px-3 py-2 text-sm hover:bg-gray-100"
                >
                  {preset.icon}
                  <span className="ml-2">{preset.label}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Input Bar */}
      <div className="flex px-2 gap-2 mb-2">
        <input
          className="flex-1 border border-gray-300 px-3 py-1 rounded text-sm"
          placeholder="Ask AION something..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && sendPrompt()}
        />
        <button
          onClick={sendPrompt}
          disabled={loading}
          className="bg-blue-600 text-white px-4 py-1 rounded text-sm"
        >
          Ask
        </button>
      </div>

      {/* Output */}
      <div className="flex-1 bg-gray-50 p-3 rounded overflow-y-auto text-sm whitespace-pre-wrap">
        {messages.length === 0 ? (
          <p className="text-gray-400">Waiting for AION...</p>
        ) : (
          messages.map((msg: any, idx: number) => (
            <div key={idx}>{typeof msg === 'string' ? msg : msg?.content ?? '[Invalid message]'}</div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}