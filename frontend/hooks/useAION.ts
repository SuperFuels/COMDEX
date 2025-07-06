import { useEffect, useRef, useState } from 'react';
import axios from 'axios';

interface Message {
  role: 'user' | 'aion' | 'system' | 'data' | 'stub';
  content: string;
  status?: 'pending' | 'success' | 'error';
}

interface CommandMeta {
  name: string;
  description: string;
  endpoint: string;
  method: 'GET' | 'POST';
  stub?: boolean;
}

export default function useAION(side: 'left' | 'right') {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [tokenUsage, setTokenUsage] = useState<number | null>(null);
  const [availableCommands, setAvailableCommands] = useState<CommandMeta[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  const append = (role: Message['role'], content: string, status?: Message['status']) => {
    setMessages((prev) => [...prev, { role, content, status }]);
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
      const res = await axios.post('/api/aion/command', { command });
      const { message, output, error, stub, label } = res.data;

      if (error) {
        append('system', `❌ ${error}`, 'error');
      } else if (stub) {
        append('stub', message || `🛠️ Stub command "${command}"`, 'success');
      } else if (output) {
        append('data', `📤 ${output}`, 'success');
      } else {
        append('aion', message || `✅ ${label || command} completed.`, 'success');
      }
    } catch (err: any) {
      append('system', `❌ Command failed: ${err.message}`, 'error');
    }

    setLoading(false);
    setInput('');
  };

  const callEndpoint = async (
    endpoint: string,
    label: string,
    method: 'get' | 'post' = 'post'
  ) => {
    append('system', `📡 Fetching ${label}...`, 'pending');

    if (endpoint.startsWith('stub:')) {
      append('stub', `🛠️ Stub command '${label}' not yet implemented.`, 'success');
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

      append('aion', `✅ ${label}:\n${formatted}`, 'success');
    } catch (err: any) {
      append('system', `❌ ${label} error: ${err.message}`, 'error');
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

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    const boot = async () => {
      if (side === 'left') {
        append('system', '🟢 Booting AION Terminal...', 'success');
        await fetchCommandRegistry();
        await sendInitialPrompt();
      }
    };
    boot();
  }, [side]);

  return {
    input,
    setInput,
    messages,
    loading,
    sendPrompt,
    sendCommand,
    callEndpoint,
    bottomRef,
    tokenUsage,
    availableCommands,
    fetchCommandRegistry,
  };
}