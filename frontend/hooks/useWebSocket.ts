// frontend/hooks/useWebSocket.ts
import { useEffect, useRef, useState } from 'react';

// ✅ Helper to convert NEXT_PUBLIC_API_URL to WSS WebSocket endpoint
function getWssUrl(path: string): string {
  const apiBase = process.env.NEXT_PUBLIC_API_URL || '';
  const wsProtocol =
    typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss' : 'ws';

  // Strip `/api` suffix if present to match FastAPI ws routes (e.g. /ws/codex)
  const base = apiBase.replace(/^http/, wsProtocol).replace(/\/api\/?$/, '');

  return `${base}${path}`;
}

export default function useWebSocket(
  path: string, // example: "/ws/codex"
  onMessage: (data: any) => void,
  filterType?: string[] // previously filterEvent, renamed for clarity
) {
  const socketRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const url = getWssUrl(path);
    const socket = new WebSocket(url);
    socketRef.current = socket;

    socket.onopen = () => setConnected(true);
    socket.onclose = () => setConnected(false);
    socket.onerror = () => setConnected(false);

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (!data?.type || !onMessage) return;
        if (filterType && !filterType.includes(data.type)) return;
        onMessage(data);
      } catch (err) {
        console.warn('WebSocket parse error:', err);
      }
    };

    return () => {
      socket.close();
    };
  }, [path, onMessage, filterType?.join(',')]);

  const emit = (event: string, data: any) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ event, data }));
    } else {
      console.warn('WebSocket not connected, cannot emit:', event);
    }
  };

  return {
    socket: socketRef.current,
    connected,
    emit,
  };
}