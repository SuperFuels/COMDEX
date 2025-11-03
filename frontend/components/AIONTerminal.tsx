// frontend/components/AIONTerminal.tsx

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
import ContainerStatus from '@/components/AION/ContainerStatus';
import GlyphGrid from './AION/GlyphGrid';
import GlyphInspector from './AION/GlyphInspector';
import ContainerMap from '../../Glyph_Net_Browser/src/components/maps/ContainerMap2D';
import GlyphMutator from './AION/GlyphMutator';
import TessarisVisualizer from '@/components/AION/TessarisVisualizer';
import { ScrollArea } from "@/components/ui/scroll-area";
import { Input } from "@/components/ui/input";

const baseUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/+$/, '') || '';

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
  const [selectedGlyph, setSelectedGlyph] = useState<null | { coord: string; data: any }>(null);
  const [showGlyphMutator, setShowGlyphMutator] = useState(false);
  const [showTessarisTree, setShowTessarisTree] = useState(false);

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
      const res = await fetch(`${baseUrl}/aion/sync-messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages }),
      });
      const result = await res.json();
      alert('✅ Synced to memory.');
    } catch (err) {
      alert('❌ Sync failed.');
      console.error(err);
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
        const res = await fetch(`${baseUrl}/aion/command/registry`);
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
      fetch(`${baseUrl}/aion/containers`)
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

  const teleportToContainer = async (id: string) => {
    try {
      const res = await fetch(`${baseUrl}/aion/teleport`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target: id }),
      });
      const result = await res.json();
      if (res.ok) {
        alert(`🌀 Teleported to ${id}`);
      } else {
        alert(`❌ Teleport failed: ${result.detail || 'Unknown error'}`);
      }
    } catch (err) {
      alert("❌ Teleport error. See console for details.");
      console.error(err);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* 🌐 Input Toolbar */}
      <div className="relative flex items-center px-4 gap-2 py-2">
        <div className="relative flex-1">
          <Input
            className="w-full pr-8 text-sm"
            placeholder={side === 'left' ? 'Type command or select preset...' : 'Ask AION...'}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) =>
              e.key === 'Enter' && (side === 'left' ? handleSubmit() : sendPrompt())
            }
          />
          <button
            onClick={() => setDropdownOpen(!dropdownOpen)}
            className="absolute right-2 top-1/2 transform -translate-y-1/2 text-gray-400"
          >
            <FaChevronDown />
          </button>

          {dropdownOpen && (
            <ScrollArea className="absolute left-0 top-10 w-full bg-white border border-gray-200 rounded shadow-lg z-10 max-h-60 overflow-auto">
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
            </ScrollArea>
          )}
        </div>

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

        <button onClick={syncMemory} className="text-blue-600 text-sm" title="Sync"><FaSync /></button>
        <button onClick={handleExport} className="text-gray-600 text-sm" title="Export"><FaFileExport /></button>
        <button onClick={() => setAutoRefresh((p) => !p)} className="text-gray-600 text-sm" title="Auto Refresh"><FaRedo /> {autoRefresh ? '🔁' : '⏸️'}</button>
        <button
          onClick={side === 'left' ? handleSubmit : sendPrompt}
          disabled={loading}
          className={`px-4 py-1 rounded text-sm text-white ${side === 'left' ? 'bg-blue-600' : 'bg-green-600'}`}
        >
          {side === 'left' ? '➤ Run' : 'Ask'}
        </button>
      </div>

      {/* 🔽 Output and Visuals */}
      <div className="flex-1 bg-gray-50 px-4 pt-4 pb-4 rounded overflow-y-auto text-sm whitespace-pre-wrap border border-gray-200 mx-2">
        {/* Message List */}
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
                <div>{msg.content ?? '[Invalid message]'}</div>
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

        {/* ✅ All Additional Runtime UI Sections Below */}
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

        {/* 🔍 Visual Tree + Glyphs */}
        {status?.context?.tessaris_snapshot && (
          <div className="mt-6">
            <div
              className="flex justify-between items-center cursor-pointer bg-gray-100 px-3 py-2 rounded border border-gray-300"
              onClick={() => setShowTessarisTree(!showTessarisTree)}
            >
              <h3 className="text-sm font-semibold text-gray-700">🌳 Tessaris Logic Tree</h3>
              <span className="text-xs text-blue-600">{showTessarisTree ? 'Hide ▲' : 'Show ▼'}</span>
            </div>
            {showTessarisTree && (
              <div className="border border-gray-200 rounded bg-white p-2 mt-2">
                <TessarisVisualizer tree={status.context.tessaris_snapshot} onNodeClick={(node) => console.log('🧠 Clicked node:', node)} />
              </div>
            )}
          </div>
        )}

        {status?.context?.current_container?.cubes && (
          <>
            <h3 className="text-sm text-gray-500 mt-4">🧩 Glyph Grid:</h3>
            <GlyphGrid
              cubes={status.context.current_container.cubes}
              onGlyphClick={(coord, data) => setSelectedGlyph({ coord, data })}
              tick={status.context?.tick ?? 0}
            />
          </>
        )}

        {selectedGlyph && (
          <GlyphInspector
            coord={selectedGlyph.coord}
            data={selectedGlyph.data}
            onClose={() => setSelectedGlyph(null)}
          />
        )}

        {selectedGlyph && status?.context?.current_container?.id && (
          <div className="mt-4 border-t border-gray-200 pt-4">
            <h3 className="text-sm text-gray-600">🧬 Glyph Mutator</h3>
            <GlyphMutator
              containerId={status.context.current_container.id}
              coord={selectedGlyph.coord}
              glyphData={selectedGlyph.data}
              onMutationComplete={() => {
                callEndpoint('status', 'Refreshing after mutation');
                setSelectedGlyph(null);
              }}
            />
          </div>
        )}

        {showGlyphMutator && selectedGlyph && (
          <div className="fixed top-0 right-0 w-[420px] h-full bg-white border-l shadow-xl z-50 overflow-y-auto p-4">
            <GlyphMutator
              containerId={status.context?.current_container?.id}
              coord={selectedGlyph.coord}
              glyphData={selectedGlyph.data}
              onMutationComplete={() => {
                callEndpoint('status', 'Refreshing after mutation');
                setShowGlyphMutator(false);
              }}
            />
          </div>
        )}

        {/* 🗺️ Map & Breadcrumbs */}
        {status?.context?.container_map && (
          <div className="mt-4">
            <ContainerMap
              mapData={status.context.container_map}
              activeId={status.context?.current_container?.id}
              onContainerClick={(id) => teleportToContainer(id)}
            />
          </div>
        )}

        {status?.context?.container_path && (
          <div className="mt-4 text-xs text-gray-600">
            <p>🧭 Path: {status.context.container_path.join(' → ')}</p>
          </div>
        )}

        {tokenUsage && (
          <div className="mt-2 text-xs text-gray-400">
            🧠 Token usage: {tokenUsage} tokens
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* 🔽 Container Summary */}
      <div className="border-t border-gray-200 p-2">
        <ContainerStatus />
      </div>
    </div>
  );
}