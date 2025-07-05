// AIONTerminal.tsx
import React, { useState, useEffect } from 'react';
import {
  FaBolt, FaPlay, FaCogs, FaBrain, FaBullseye, FaSync, FaTerminal
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

  const [command, setCommand] = useState('');

  const presets = [
    { label: 'Run Full Learning Cycle', value: 'run-learning-cycle', icon: <FaPlay className="text-blue-600" /> },
    { label: 'Nightly Dream Trigger', value: 'run-dream', icon: <FaBolt className="text-yellow-500" /> },
    { label: 'Boot Next Skill', value: 'boot-skill', icon: <FaCogs className="text-gray-600" /> },
    { label: 'Reflect on Skills', value: 'skill-reflect', icon: <FaBrain className="text-purple-500" /> },
    { label: 'Check Goals', value: 'goal', icon: <FaBullseye className="text-green-600" /> },
    { label: 'System Status', value: 'status', icon: <FaSync className="text-indigo-600" /> },
  ];

  const handleCommand = async () => {
    if (!command.trim()) return;

    const method: 'get' | 'post' = command === 'goal' || command === 'status' ? 'get' : 'post';
    const url = `/api/aion/${command}`;
    await callEndpoint(url, `Command: ${command}`, method);
    setCommand('');
  };

  const handlePresetClick = async (presetValue: string) => {
    const method: 'get' | 'post' = presetValue === 'goal' || presetValue === 'status' ? 'get' : 'post';
    const url = `/api/aion/${presetValue}`;
    await callEndpoint(url, `Preset: ${presetValue}`, method);
  };

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="flex flex-col h-full">
      {/* Unified Command + Presets */}
      <div className="flex gap-2 px-2 py-1">
        <input
          className="flex-1 border border-gray-300 px-3 py-1 rounded text-sm"
          placeholder="Type command (e.g. run-dream) or choose preset below..."
          value={command}
          onChange={(e) => setCommand(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleCommand()}
        />
        <button
          onClick={handleCommand}
          disabled={loading}
          className="bg-blue-600 text-white px-4 py-1 rounded text-sm"
        >
          <FaTerminal />
        </button>
      </div>

      {/* Presets */}
      <div className="grid grid-cols-3 gap-2 px-2 py-1">
        {presets.map((preset) => (
          <button
            key={preset.value}
            onClick={() => handlePresetClick(preset.value)}
            className="flex items-center px-2 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded shadow-sm"
          >
            {preset.icon}
            <span className="ml-2">{preset.label}</span>
          </button>
        ))}
      </div>

      {/* Output Terminal */}
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