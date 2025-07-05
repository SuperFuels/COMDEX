// frontend/components/AIONTerminal.tsx
import React, { useState, useEffect } from 'react';
import {
  FaBolt, FaPlay, FaCogs, FaBrain, FaBullseye, FaSync, FaChevronDown
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

  const presets = [
    { label: 'Run Full Learning Cycle', value: 'run-learning-cycle', icon: <FaPlay className="text-blue-600" /> },
    { label: 'Nightly Dream Trigger', value: 'run-dream', icon: <FaBolt className="text-yellow-500" /> },
    { label: 'Boot Next Skill', value: 'boot-skill', icon: <FaCogs className="text-gray-600" /> },
    { label: 'Reflect on Skills', value: 'skill-reflect', icon: <FaBrain className="text-purple-500" /> },
    { label: 'Check Goals', value: 'goal', icon: <FaBullseye className="text-green-600" /> },
    { label: 'System Status', value: 'status', icon: <FaSync className="text-indigo-600" /> },
  ];

  const handleSubmit = async () => {
    if (!input.trim()) return;
    const method: 'get' | 'post' = input === 'goal' || input === 'status' ? 'get' : 'post';
    const url = `/api/aion/${input}`;
    await callEndpoint(url, `Command: ${input}`, method);
    setInput('');
  };

  const handlePresetClick = async (value: string) => {
    const method: 'get' | 'post' = value === 'goal' || value === 'status' ? 'get' : 'post';
    const url = `/api/aion/${value}`;
    await callEndpoint(url, `Preset: ${value}`, method);
    setInput('');
    setDropdownOpen(false);
  };

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="flex flex-col h-full">
      {side === 'left' ? (
        // 🔧 LEFT: Command Bar with Presets
        <div className="relative flex px-2 gap-2 py-1">
          <div className="relative flex-1">
            <input
              className="w-full border border-gray-300 px-3 py-1 rounded text-sm"
              placeholder="Type command (e.g. run-dream) or select preset..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
            />
            <button
              onClick={() => setDropdownOpen(!dropdownOpen)}
              className="absolute right-2 top-1/2 transform -translate-y-1/2 text-gray-400"
            >
              <FaChevronDown />
            </button>

            {dropdownOpen && (
              <div className="absolute left-0 top-10 w-full bg-white border border-gray-200 rounded shadow-lg z-10 max-h-60 overflow-auto">
                {presets.map((preset) => (
                  <button
                    key={preset.value}
                    onClick={() => handlePresetClick(preset.value)}
                    className="flex items-center w-full px-3 py-2 text-sm hover:bg-gray-100"
                  >
                    {preset.icon}
                    <span className="ml-2">{preset.label}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
          <button
            onClick={handleSubmit}
            disabled={loading}
            className="bg-blue-600 text-white px-4 py-1 rounded text-sm"
          >
            ➤ Run
          </button>
        </div>
      ) : (
        // 💬 RIGHT: Prompt Bar with Ask button
        <div className="relative flex px-2 gap-2 py-1">
          <input
            className="w-full border border-gray-300 px-3 py-1 rounded text-sm"
            placeholder="Ask AION something..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && sendPrompt()}
          />
          <button
            onClick={sendPrompt}
            disabled={loading}
            className="bg-green-600 text-white px-4 py-1 rounded text-sm"
          >
            Ask
          </button>
        </div>
      )}

      {/* 🖥 Output Terminal */}
      <div className="flex-1 bg-gray-50 p-3 rounded overflow-y-auto text-sm whitespace-pre-wrap">
        {messages.length === 0 ? (
          <p className="text-gray-400">Waiting for AION...</p>
        ) : (
          messages.map((msg: any, idx: number) => (
            <div key={idx}>
              {typeof msg === 'string' ? msg : msg?.content ?? '[Invalid message]'}
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}