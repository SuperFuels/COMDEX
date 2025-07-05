// hooks/useAION.ts
import { useEffect, useRef, useState } from 'react';
import axios from 'axios';

interface Message {
  role: 'user' | 'aion' | 'system';
  content: string;
}

export default function useAION() {
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
      const res = await axios.post('/api/aion/prompt', { prompt: input });
      append('aion', res.data.reply || '(no response)');
    } catch (err: any) {
      append('system', `❌ AION error: ${err.message}`);
    }

    setLoading(false);
    setInput('');
  };

  const callEndpoint = async (endpoint: string, label: string) => {
    append('system', `📡 Fetching ${label}...`);
    try {
      const res = await axios.get(endpoint);
      append('aion', `✅ ${label}:\n${JSON.stringify(res.data, null, 2)}`);
    } catch (err: any) {
      append('system', `❌ ${label} error: ${err.message}`);
    }
  };

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    const startup = async () => {
      append('system', '🟢 Booting AION Terminal...');
      await sendInitialPrompt();
    };
    startup();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const sendInitialPrompt = async () => {
    append('user', 'Provide me with an update on your overall progress & how you are feeling.');
    try {
      const res = await axios.post('/api/aion/prompt', {
        prompt: 'Provide me with an update on your overall progress & how you are feeling.',
      });
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