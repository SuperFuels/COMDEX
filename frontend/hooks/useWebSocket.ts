// File: frontend/hooks/useWebSocket.ts

import { useEffect, useRef, useState } from 'react';

// ✅ Converts NEXT_PUBLIC_API_URL into a valid WebSocket URL
function getWssUrl(path: string): string {
  const apiBase = process.env.NEXT_PUBLIC_API_URL || '';

  const wsProtocol =
    typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss' : 'ws';

  // ✅ Correctly replaces full http:// or https:// prefix
  const base = apiBase
    .replace(/^https?:\/\/?/, `${wsProtocol}://`)
    .replace(/\/api\/?$/, ''); // ✅ Removes trailing /api or /api/

  return `${base}${path}`;
}

export default function useWebSocket(
  path: string, // e.g., "/ws/updates"
  onMessage: (data: any) => void,
  filterType?: string[] // Optional: filter only specific message types
) {
  const socketRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const url = getWssUrl(path);
    const socket = new WebSocket(url);
    socketRef.current = socket;

    socket.onopen = () => setConnected(true);
    socket.onclose = () => setConnected(false);
    socket.onerror = (e) => {
      console.warn('WebSocket error:', e);
      setConnected(false);
    };

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