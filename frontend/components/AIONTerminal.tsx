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
    tokenUsage
  } = useAION(side);

  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [activeFilter, setActiveFilter] = useState<'all' | 'aion' | 'user' | 'system'>('all');

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

  const getMessageColor = (role: string) => {
    switch (role) {
      case 'aion': return 'text-black';
      case 'user': return 'text-blue-600';
      case 'system':
        return 'text-purple-600';
      default:
        return 'text-green-600';
    }
  };

  const filteredMessages = messages.filter((msg) => {
    if (activeFilter === 'all') return true;
    return msg.role === activeFilter;
  });

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="flex flex-col h-full">
      {side === 'left' ? (
        <div className="relative flex px-4 gap-2 py-2">
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
              className="absolute right-1.5 top-1/2 transform -translate-y-1/2 text-gray-400"
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
        <div className="relative flex px-4 gap-2 py-2">
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

      {/* 🔍 Filter Tabs */}
      <div className="flex justify-start gap-2 px-4 mt-1 text-sm">
        {['all', 'aion', 'user', 'system'].map((filter) => (
          <button
            key={filter}
            onClick={() => setActiveFilter(filter as any)}
            className={`px-2 py-0.5 rounded ${
              activeFilter === filter
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-700'
            }`}
          >
            {filter.toUpperCase()}
          </button>
        ))}
      </div>

      {/* 🖥 Output Terminal */}
      <div className="flex-1 bg-gray-50 px-4 pt-4 pb-4 rounded overflow-y-auto text-sm whitespace-pre-wrap border border-gray-200 mx-2">
        {filteredMessages.length === 0 ? (
          <p className="text-gray-400">Waiting for AION...</p>
        ) : (
          filteredMessages.map((msg: any, idx: number) => (
            <div key={idx} className={getMessageColor(msg.role)}>
              {typeof msg === 'string' ? msg : msg?.content ?? '[Invalid message]'}
            </div>
          ))
        )}
        {tokenUsage && (
          <div className="mt-2 text-xs text-gray-400">🧠 Token usage: {tokenUsage} tokens</div>
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}