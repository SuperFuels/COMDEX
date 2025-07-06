import { useEffect, useRef, useState } from 'react';
import axios from 'axios';

interface Message {
  role: 'user' | 'aion' | 'system' | 'data' | 'stub';
  content: string;
}

export default function useAION(side: 'left' | 'right') {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [tokenUsage, setTokenUsage] = useState<number | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const append = (role: Message['role'], content: string) => {
    setMessages((prev) => [...prev, { role, content }]);
  };

  const sendPrompt = async () => {
    if (!input.trim()) return;
    append('user', input);
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

      append('aion', formatted);
    } catch (err: any) {
      append('system', `❌ AION error: ${err.message}`);
    }

    setLoading(false);
    setInput('');
  };

  const sendCommand = async (command: string) => {
    if (!command.trim()) return;
    append('user', command);
    setLoading(true);

    try {
      const res = await axios.post('/api/aion/command', { command });
      const { message, output, error, stub, label } = res.data;

      if (error) {
        append('system', `❌ ${error}`);
      } else if (stub) {
        append('stub', message || `🛠️ Stub command "${command}"`);
      } else if (output) {
        append('data', `📤 ${output}`);
      } else {
        append('aion', message || `✅ ${label || command} completed.`);
      }
    } catch (err: any) {
      append('system', `❌ Command failed: ${err.message}`);
    }

    setLoading(false);
    setInput('');
  };

  const callEndpoint = async (
    endpoint: string,
    label: string,
    method: 'get' | 'post' = 'post'
  ) => {
    append('system', `📡 Fetching ${label}...`);

    if (endpoint.startsWith('stub:')) {
      append('stub', `🛠️ Stub command '${label}' not yet implemented.`);
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

      append('aion', `✅ ${label}:\n${formatted}`);
    } catch (err: any) {
      append('system', `❌ ${label} error: ${err.message}`);
    }
  };

  const sendInitialPrompt = async () => {
    const prompt = 'Provide me with an update on your overall progress & how you are feeling.';
    append('user', prompt);
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

      append('aion', formatted);
    } catch (err: any) {
      append('system', `❌ Startup failed: ${err.message}`);
    }
  };

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    const boot = async () => {
      if (side === 'left') {
        append('system', '🟢 Booting AION Terminal...');
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
  };
}