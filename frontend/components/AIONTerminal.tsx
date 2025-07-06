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
    sendCommand,
    bottomRef,
    tokenUsage
  } = useAION(side);

  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [activeFilter, setActiveFilter] = useState<'all' | 'aion' | 'user' | 'system' | 'data' | 'stub'>('all');

  const presets = [
    { label: 'Run Full Learning Cycle', value: 'run_learning_cycle', icon: <FaPlay className="text-blue-600" />, desc: 'Triggers the full AION learning script' },
    { label: 'Nightly Dream Trigger', value: 'run_dream', icon: <FaBolt className="text-yellow-500" />, desc: 'Runs a simulated dream cycle' },
    { label: 'Boot Next Skill', value: 'boot_skill', icon: <FaCogs className="text-gray-600" />, desc: 'Boots the next queued skill from bootloader' },
    { label: 'Reflect on Skills', value: 'skill-reflect', icon: <FaBrain className="text-purple-500" />, desc: 'Generates a reflection on current skill progress' },
    { label: 'Check Goals', value: 'goal', icon: <FaBullseye className="text-green-600" />, desc: 'Shows current goals and milestones' },
    { label: 'System Status', value: 'status', icon: <FaSync className="text-indigo-600" />, desc: 'Returns current engine status' },
    { label: 'Show Boot Progress', value: 'show-boot-progress', icon: <FaCogs className="text-gray-500" />, desc: 'Displays bootloader learning queue', stub: true },
    { label: 'Sync State', value: 'sync-state', icon: <FaSync className="text-blue-400" />, desc: 'Resyncs internal state tracker', stub: true }
  ];

  const handleSubmit = async () => {
    if (!input.trim()) return;
    await sendCommand(input.trim());
    setInput('');
  };

  const handlePresetClick = async (value: string) => {
    await sendCommand(value);
    setInput('');
    setDropdownOpen(false);
  };

  const getMessageColor = (role: string) => {
    switch (role) {
      case 'aion': return 'text-black';
      case 'user': return 'text-blue-600';
      case 'system': return 'text-purple-600';
      case 'data': return 'text-green-600';
      case 'stub': return 'text-gray-500 italic';
      default: return 'text-gray-700';
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
      <div className="relative flex px-4 gap-2 py-2">
        <div className="relative flex-1">
          <input
            className="w-full border border-gray-300 px-3 py-1 rounded text-sm"
            placeholder={side === 'left' ? "Type command (e.g. run_dream) or select preset..." : "Ask AION something..."}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && (side === 'left' ? handleSubmit() : sendPrompt())}
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
                  className="flex flex-col items-start w-full px-3 py-2 text-sm hover:bg-gray-100 text-left"
                >
                  <div className="flex items-center gap-2">
                    {preset.icon}
                    <span className="font-medium">{preset.label}</span>
                  </div>
                  <div className="text-xs text-gray-500 ml-6">{preset.desc}</div>
                </button>
              ))}
            </div>
          )}
        </div>

        <select
          className="border border-gray-300 rounded text-sm px-2"
          value={activeFilter}
          onChange={(e) => setActiveFilter(e.target.value as any)}
        >
          <option value="all">All</option>
          <option value="aion">AION</option>
          <option value="user">User</option>
          <option value="system">System</option>
          <option value="data">Data Output</option>
          <option value="stub">Boot / Stub</option>
        </select>

        <button
          onClick={side === 'left' ? handleSubmit : sendPrompt}
          disabled={loading}
          className={`px-4 py-1 rounded text-sm text-white ${side === 'left' ? 'bg-blue-600' : 'bg-green-600'}`}
        >
          {side === 'left' ? '➤ Run' : 'Ask'}
        </button>
      </div>

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