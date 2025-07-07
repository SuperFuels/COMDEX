import React, { useState, useEffect } from 'react';
import { FaPlay, FaChevronDown, FaSave, FaSync, FaFileExport, FaEdit } from 'react-icons/fa';
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
    setMessages,
    sendPrompt,
    callEndpoint,
    sendCommand,
    bottomRef,
    tokenUsage,
    availableCommands,
    setAvailableCommands, // <-- Required if your hook uses useState
  } = useAION(side);

  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [activeFilter, setActiveFilter] = useState<'all' | 'aion' | 'user' | 'system' | 'data' | 'stub'>('all');
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editedContent, setEditedContent] = useState<string>("");

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
    const a = document.createElement("a");
    a.href = url;
    a.download = "aion_terminal_export.txt";
    a.click();
    URL.revokeObjectURL(url);
  };

  const syncMemory = async () => {
    try {
      const res = await fetch("/api/aion/sync-messages", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages }),
      });
      const result = await res.json();
      alert("✅ Synced to memory.");
    } catch (err) {
      alert("❌ Sync failed.");
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
      role === 'aion' ? 'text-black' :
      role === 'user' ? 'text-blue-600' :
      role === 'system' ? 'text-purple-600' :
      role === 'data' ? 'text-green-600' :
      role === 'stub' ? 'text-gray-500 italic' :
      'text-gray-700';

    const statusStyle =
      status === 'error' ? 'text-red-500' :
      status === 'pending' ? 'animate-pulse text-yellow-600' :
      '';

    return `${base} ${statusStyle}`;
  };

  const getStatusIcon = (status?: string) => {
    return status === 'pending' ? '🟡' :
           status === 'error' ? '❌' :
           status === 'success' ? '✅' : '';
  };

  const filteredMessages = messages.filter((msg) => {
    if (activeFilter === 'all') return true;
    return msg.role === activeFilter;
  });

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // 🔁 Fetch command registry on mount
  useEffect(() => {
    const fetchCommands = async () => {
      try {
        const res = await fetch('/api/aion/command/registry');
        const data = await res.json();
        if (Array.isArray(data)) {
          setAvailableCommands(data); // requires your hook to expose setAvailableCommands
        }
      } catch (err) {
        console.error('Failed to fetch command registry', err);
      }
    };

    fetchCommands();
  }, []);

  return (
    <div className="flex flex-col h-full">
      <div className="relative flex items-center px-4 gap-2 py-2">
        {/* Input */}
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
          title="Filter messages"
        >
          <option value="all">All</option>
          <option value="aion">AION</option>
          <option value="user">User</option>
          <option value="system">System</option>
          <option value="data">Data</option>
          <option value="stub">Stub</option>
        </select>

        {/* Action Buttons */}
        <button onClick={syncMemory} title="Sync to memory" className="text-blue-600 text-sm">
          <FaSync />
        </button>
        <button onClick={handleExport} title="Export log" className="text-gray-600 text-sm">
          <FaFileExport />
        </button>

        {/* Submit Button */}
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
        {filteredMessages.length === 0 ? (
          <p className="text-gray-400">Waiting for AION...</p>
        ) : (
          filteredMessages.map((msg, idx) => (
            <div key={idx} className={`${getMessageColor(msg.role, msg.status)} flex items-start justify-between mb-2`}>
              <div className="flex-1">
                {getStatusIcon(msg.status)}{" "}
                {editingIndex === idx ? (
                  <div className="flex gap-2 items-center">
                    <input
                      value={editedContent}
                      onChange={(e) => setEditedContent(e.target.value)}
                      className="border px-2 py-1 rounded text-sm w-full"
                    />
                    <button onClick={() => handleEditSave(idx)} className="text-green-600 text-sm"><FaSave /></button>
                  </div>
                ) : (
                  <>
                    <div>{msg.content ?? '[Invalid message]'}</div>
                    {(msg.role === 'aion' || msg.role === 'system' || msg.role === 'data') && (
                      <div className="mt-1 flex gap-2 text-xs">
                        <button
                          onClick={() => alert('✅ Approved!')}
                          className="bg-green-100 hover:bg-green-200 text-green-700 px-2 py-1 rounded"
                        >
                          ✅ Approve
                        </button>
                        <button
                          onClick={() => {
                            const blob = new Blob([msg.content || ''], { type: 'application/pdf' });
                            const url = URL.createObjectURL(blob);
                            const a = document.createElement("a");
                            a.href = url;
                            a.download = `aion_message_${idx}.pdf`;
                            a.click();
                            URL.revokeObjectURL(url);
                          }}
                          className="bg-blue-100 hover:bg-blue-200 text-blue-700 px-2 py-1 rounded"
                        >
                          📥 Download
                        </button>
                      </div>
                    )}
                  </>
                )}
              </div>
              {editingIndex !== idx && (
                <button
                  onClick={() => {
                    setEditingIndex(idx);
                    setEditedContent(msg.content || "");
                  }}
                  className="ml-2 text-gray-500 text-xs"
                >
                  <FaEdit />
                </button>
              )}
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