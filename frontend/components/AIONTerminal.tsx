// File: frontend/components/AIONTerminal.tsx

import React, { useState, useEffect } from 'react';
import {
  FaPlay,
  FaChevronDown,
  FaSave,
  FaSync,
  FaFileExport,
  FaEdit,
  FaRedo,
} from 'react-icons/fa';
import useAION from '../hooks/useAION';
import ContainerStatus from '@/components/AION/ContainerStatus';// ✅ Add component import

interface AIONTerminalProps {
  side: 'left' | 'right';
}

export default function AIONTerminal({ side }: AIONTerminalProps) {
  const {
    input,
    setInput,
    loading,
    messages,
    setMessages,
    sendPrompt,
    callEndpoint,
    sendCommand,
    bottomRef,
    tokenUsage,
    availableCommands,
    setAvailableCommands,
    status,
    setStatus,
  } = useAION(side, `${side.toUpperCase()} Terminal`);

  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [activeFilter, setActiveFilter] = useState<'all' | 'aion' | 'user' | 'system' | 'data' | 'stub'>('all');
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editedContent, setEditedContent] = useState<string>('');
  const [autoRefresh, setAutoRefresh] = useState(true);

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

  const handleExport = () => {
    const exportText = messages.map((m) => `[${m.role}] ${m.content}`).join('\n');
    const blob = new Blob([exportText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'aion_terminal_export.txt';
    a.click();
    URL.revokeObjectURL(url);
  };

  const syncMemory = async () => {
    try {
      const res = await fetch('/api/aion/sync-messages', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages }),
      });
      const result = await res.json();
      alert('✅ Synced to memory.');
    } catch (err) {
      alert('❌ Sync failed.');
    }
  };

  const handleEditSave = (index: number) => {
    const newMessages = [...messages];
    newMessages[index].content = editedContent;
    setMessages(newMessages);
    setEditingIndex(null);
  };

  const getMessageColor = (role: string, status?: string) => {
    const base =
      role === 'aion'
        ? 'text-black'
        : role === 'user'
        ? 'text-blue-600'
        : role === 'system'
        ? 'text-purple-600'
        : role === 'data'
        ? 'text-green-600'
        : role === 'stub'
        ? 'text-gray-500 italic'
        : 'text-gray-700';

    const statusStyle =
      status === 'error'
        ? 'text-red-500'
        : status === 'pending'
        ? 'animate-pulse text-yellow-600'
        : '';

    return `${base} ${statusStyle}`;
  };

  const getStatusIcon = (status?: string) => {
    return status === 'pending'
      ? '🟡'
      : status === 'error'
      ? '❌'
      : status === 'success'
      ? '✅'
      : '';
  };

  const filteredMessages = messages.filter((msg) => {
    if (activeFilter === 'all') return true;
    return msg.role === activeFilter;
  });

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    const fetchCommands = async () => {
      try {
        const res = await fetch('/api/aion/command/registry');
        const data = await res.json();
        if (Array.isArray(data)) {
          setAvailableCommands(data);
        }
      } catch (err) {
        console.error('Failed to fetch command registry', err);
      }
    };

    fetchCommands();
  }, []);

  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(() => {
      callEndpoint('status', 'Refreshing status');
      fetch('/api/aion/containers')
        .then((res) => res.json())
        .then((data) => {
          if (data?.containers) {
            setStatus((prev: any) => ({
              ...prev,
              context: {
                ...(prev?.context || {}),
                available_containers: data.containers,
              },
            }));
          }
        });
    }, 10000);
    return () => clearInterval(interval);
  }, [autoRefresh]);

  const teleportToContainer = (id: string) => sendCommand(`teleport ${id}`);

  return (
    <div className="flex flex-col h-full">
      <div className="relative flex items-center px-4 gap-2 py-2">
        {/* Input */}
        <div className="relative flex-1">
          <input
            className="w-full border border-gray-300 px-3 py-1 rounded text-sm"
            placeholder={side === 'left' ? 'Type command or select preset...' : 'Ask AION...'}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) =>
              e.key === 'Enter' && (side === 'left' ? handleSubmit() : sendPrompt())
            }
          />
          <button
            onClick={() => setDropdownOpen(!dropdownOpen)}
            className="absolute right-1.5 top-1/2 transform -translate-y-1/2 text-gray-400"
          >
            <FaChevronDown />
          </button>
          {dropdownOpen && (
            <div className="absolute left-0 top-10 w-full bg-white border border-gray-200 rounded shadow-lg z-10 max-h-60 overflow-auto">
              {availableCommands.map((cmd) => (
                <button
                  key={cmd.name}
                  onClick={() => handlePresetClick(cmd.name)}
                  className="flex flex-col items-start w-full px-3 py-2 text-sm hover:bg-gray-100 text-left"
                >
                  <div className="flex items-center gap-2">
                    <FaPlay className="text-blue-500" />
                    <span className="font-medium">{cmd.name}</span>
                    {cmd.stub && <span className="ml-2 text-xs text-orange-500">[stub]</span>}
                  </div>
                  <div className="text-xs text-gray-500 ml-6">{cmd.description || cmd.endpoint}</div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Filter */}
        <select
          className="border border-gray-300 rounded text-sm px-2 py-1 w-28 text-gray-700 bg-white"
          value={activeFilter}
          onChange={(e) => setActiveFilter(e.target.value as any)}
        >
          <option value="all">All</option>
          <option value="aion">AION</option>
          <option value="user">User</option>
          <option value="system">System</option>
          <option value="data">Data</option>
          <option value="stub">Stub</option>
        </select>

        {/* Buttons */}
        <button onClick={syncMemory} className="text-blue-600 text-sm" title="Sync">
          <FaSync />
        </button>
        <button onClick={handleExport} className="text-gray-600 text-sm" title="Export">
          <FaFileExport />
        </button>
        <button onClick={() => setAutoRefresh((p) => !p)} className="text-gray-600 text-sm" title="Auto Refresh">
          <FaRedo /> {autoRefresh ? '🔁' : '⏸️'}
        </button>
        <button
          onClick={side === 'left' ? handleSubmit : sendPrompt}
          disabled={loading}
          className={`px-4 py-1 rounded text-sm text-white ${side === 'left' ? 'bg-blue-600' : 'bg-green-600'}`}
        >
          {side === 'left' ? '➤ Run' : 'Ask'}
        </button>
      </div>

      {/* Output */}
      <div className="flex-1 bg-gray-50 px-4 pt-4 pb-4 rounded overflow-y-auto text-sm whitespace-pre-wrap border border-gray-200 mx-2">
        {filteredMessages.map((msg, idx) => (
          <div key={idx} className={`${getMessageColor(msg.role, msg.status)} flex items-start justify-between mb-2`}>
            <div className="flex-1">
              {getStatusIcon(msg.status)}{' '}
              {editingIndex === idx ? (
                <div className="flex gap-2 items-center">
                  <input
                    value={editedContent}
                    onChange={(e) => setEditedContent(e.target.value)}
                    className="border px-2 py-1 rounded text-sm w-full"
                  />
                  <button onClick={() => handleEditSave(idx)} className="text-green-600 text-sm">
                    <FaSave />
                  </button>
                </div>
              ) : (
                <>
                  <div>{msg.content ?? '[Invalid message]'}</div>
                </>
              )}
            </div>
            {editingIndex !== idx && (
              <button
                onClick={() => {
                  setEditingIndex(idx);
                  setEditedContent(msg.content || '');
                }}
                className="ml-2 text-gray-500 text-xs"
              >
                <FaEdit />
              </button>
            )}
          </div>
        ))}

        {/* 📦 Containers */}
        {status?.context?.available_containers && (
          <div className="mt-4 text-xs text-gray-500">
            <p>📦 Available Containers:</p>
            <ul className="list-disc ml-6">
              {status.context.available_containers.map((c: any) => (
                <li
                  key={c.id}
                  onClick={() => teleportToContainer(c.id)}
                  className={`cursor-pointer ${c.id === status?.context?.current_container ? 'font-bold text-blue-600' : ''}`}
                >
                  {c.id} {c.in_memory ? '🧠' : '📁'}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* 🗺️ Mini Map */}
        {status?.context?.container_map && (
          <div className="mt-4 text-xs text-gray-600">
            <p>🗺️ Container Map:</p>
            <pre className="ml-4 whitespace-pre-wrap">{JSON.stringify(status.context.container_map, null, 2)}</pre>
          </div>
        )}

        {/* 🧭 Breadcrumb Path */}
        {status?.context?.container_path && (
          <div className="mt-4 text-xs text-gray-600">
            <p>🧭 Path: {status.context.container_path.join(' → ')}</p>
          </div>
        )}

        {/* 🧠 Token Usage */}
        {tokenUsage && (
          <div className="mt-2 text-xs text-gray-400">
            🧠 Token usage: {tokenUsage} tokens
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* 🔍 Container Summary Component */}
      <div className="border-t border-gray-200 p-2">
        <ContainerStatus />
      </div>
    </div>
  );
}