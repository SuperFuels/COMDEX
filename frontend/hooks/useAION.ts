import { useEffect, useRef, useState } from 'react';
import axios from 'axios';
import useWebSocket from './useWebSocket'; // ✅ Add this line

type Command = {
  name: string;
  description?: string;
  endpoint?: string;
  stub?: boolean;
};

interface Message {
  role: 'user' | 'aion' | 'system' | 'data' | 'stub';
  content: string;
  status?: 'pending' | 'success' | 'error';
}

export interface AIONStatus {
  context?: {
    current_container?: string;
    available_containers?: string[];
    [key: string]: any;
  };
  [key: string]: any;
}

export default function useAION(side: 'left' | 'right', label: string = 'AION Terminal') {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [tokenUsage, setTokenUsage] = useState<number | null>(null);
  const [availableCommands, setAvailableCommands] = useState<Command[]>([]);
  const [status, setStatus] = useState<any>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const append = (role: Message['role'], content: string, status?: Message['status']) => {
    setMessages((prev) => [...prev, { role, content, status }]);
  };

  const syncMessagesToBackend = async () => {
    try {
      await axios.post('/api/aion/sync-messages', { messages });
    } catch (err: any) {
      append('system', `⚠️ Failed to sync messages: ${err.message}`, 'error');
    }
  };

  const sendPrompt = async () => {
    if (!input.trim()) return;
    append('user', input, 'pending');
    setLoading(true);

    try {
      const res = await axios.post(`/aion/prompt`, { prompt: input });
      const reply = res.data.reply || '(no response)';
      const tokens = res.data.tokens_used;
      const cost = res.data.cost_estimate;

      if (tokens) setTokenUsage(tokens);

      let formatted = reply;
      if (tokens || cost) {
        formatted += `\n\n🧮 Tokens used: ${tokens || 'N/A'}\n💸 Estimated cost: $${cost || 'N/A'}`;
      }

      append('aion', formatted, 'success');
      await syncMessagesToBackend();
    } catch (err: any) {
      append('system', `❌ AION error: ${err.message}`, 'error');
    }

    setLoading(false);
    setInput('');
  };

  const sendCommand = async (command: string) => {
    if (!command.trim()) return;
    append('user', command, 'pending');
    setLoading(true);

    try {
      const res = await axios.post('/api/aion/command', {
        command,
        side,
        label,
      });

      const { message, output, error, stub } = res.data;

      if (error) {
        append('system', `❌ ${error}`, 'error');
      } else if (stub) {
        append('stub', message || `🛠️ Stub command "${command}"`, 'success');
      } else if (output) {
        append('data', `📤 ${output}`, 'success');
      } else {
        append('aion', message || `✅ ${label || command} completed.`, 'success');
      }

      await syncMessagesToBackend();
    } catch (err: any) {
      append('system', `❌ Command failed: ${err.message}`, 'error');
    }

    setLoading(false);
    setInput('');
  };

  const callEndpoint = async (
    endpoint: string,
    labelText: string,
    method: 'get' | 'post' = 'post'
  ) => {
    append('system', `📡 Fetching ${labelText}...`, 'pending');

    if (endpoint.startsWith('stub:')) {
      append('stub', `🛠️ Stub command '${labelText}' not yet implemented.`, 'success');
      return;
    }

    try {
      const url = `/aion/${endpoint.replace(/^\/+/, '')}`;
      const res = method === 'post' ? await axios.post(url) : await axios.get(url);
      const data = res.data;

      if (data.tokens_used) setTokenUsage(data.tokens_used);

      let formatted = typeof data === 'object'
        ? JSON.stringify(data, null, 2)
        : String(data);

      if (data.tokens_used || data.cost_estimate) {
        formatted += `\n\n🧮 Tokens used: ${data.tokens_used || 'N/A'}\n💸 Estimated cost: $${data.cost_estimate || 'N/A'}`;
      }

      append('aion', `✅ ${labelText}:\n${formatted}`, 'success');
    } catch (err: any) {
      append('system', `❌ ${labelText} error: ${err.message}`, 'error');
    }
  };

  const sendInitialPrompt = async () => {
    const prompt = 'Provide me with an update on your overall progress & how you are feeling.';
    append('user', prompt, 'pending');
    try {
      const res = await axios.post(`/aion/prompt`, { prompt });

      const reply = res.data.reply || '(no response)';
      const tokens = res.data.tokens_used;
      const cost = res.data.cost_estimate;

      if (tokens) setTokenUsage(tokens);

      let formatted = reply;
      if (tokens || cost) {
        formatted += `\n\n🧮 Tokens used: ${tokens || 'N/A'}\n💸 Estimated cost: $${cost || 'N/A'}`;
      }

      append('aion', formatted, 'success');
      await syncMessagesToBackend();
    } catch (err: any) {
      append('system', `❌ Startup failed: ${err.message}`, 'error');
    }
  };

  const fetchCommandRegistry = async () => {
    try {
      const res = await axios.get('/api/aion/command/registry');
      const commands = res.data.commands || [];
      setAvailableCommands(commands);
    } catch (err: any) {
      append('system', `⚠️ Failed to load command list: ${err.message}`, 'error');
    }
  };

  const fetchStatus = async () => {
    try {
      const res = await axios.get('/aion/status');
      setStatus(res.data);
    } catch (err: any) {
      append('system', `⚠️ Failed to fetch status: ${err.message}`, 'error');
    }
  };

  // ✅ WebSocket: listen for live updates
  useWebSocket(
    process.env.NEXT_PUBLIC_SOCKET_URL || 'ws://localhost:8000/ws',
    (msg: any) => {
      if (msg.event === 'status_update' && msg.context) {
        setStatus((prev: any) => ({
          ...prev,
          context: {
            ...prev?.context,
            ...msg.context,
          },
        }));
      }

      if (msg.event === 'glyph_update' && side === 'right') {
        append('data', '🧬 Glyphs updated from WebSocket.', 'success');
      }

      if (msg.event === 'container_teleport') {
        append('system', `🧭 Teleported to: ${msg.containerId}`, 'success');
      }
    },
    ['status_update', 'glyph_update', 'container_teleport']
  );

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    const boot = async () => {
      if (side === 'left') {
        append('system', '🟢 Booting AION Terminal...', 'success');
        await fetchCommandRegistry();
        await fetchStatus();
        await sendInitialPrompt();
      }
    };
    boot();
  }, [side]);

  return {
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
    setStatus, // ✅ Keep exposed for updates
  };
}