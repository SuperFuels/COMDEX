// hooks/useAION.ts
import { useEffect, useRef, useState } from 'react';
import axios from 'axios';

interface Message {
  role: 'user' | 'aion' | 'system';
  content: string;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || '';

export default function useAION(side: 'left' | 'right') {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const append = (role: Message['role'], content: string) => {
    setMessages((prev) => [...prev, { role, content }]);
  };

  const sendPrompt = async () => {
    if (!input.trim()) return;
    append('user', input);
    setLoading(true);

    try {
      const res = await axios.post(`${API_URL}/api/aion/prompt`, { prompt: input });
      append('aion', res.data.reply || '(no response)');
    } catch (err: any) {
      append('system', `❌ AION error: ${err.message}`);
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
    try {
      const url = `${API_URL}/api/aion/${endpoint.replace(/^\/+/, '')}`; // ensure clean path
      const res = method === 'post'
        ? await axios.post(url)
        : await axios.get(url);

      const dataString = typeof res.data === 'object'
        ? JSON.stringify(res.data, null, 2)
        : String(res.data);

      append('aion', `✅ ${label}:\n${dataString}`);
    } catch (err: any) {
      append('system', `❌ ${label} error: ${err.message}`);
    }
  };

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // 🔁 Boot message only for left terminal
  useEffect(() => {
    const boot = async () => {
      if (side === 'left') {
        append('system', '🟢 Booting AION Terminal...');
        await sendInitialPrompt();
      }
    };
    boot();
  }, [side]);

  const sendInitialPrompt = async () => {
    const prompt = 'Provide me with an update on your overall progress & how you are feeling.';
    append('user', prompt);
    try {
      const res = await axios.post(`${API_URL}/api/aion/prompt`, { prompt });
      append('aion', res.data.reply || '(no response)');
    } catch (err: any) {
      append('system', `❌ Startup failed: ${err.message}`);
    }
  };

  return {
    input,
    setInput,
    messages,
    loading,
    sendPrompt,
    callEndpoint,
    bottomRef,
  };
}