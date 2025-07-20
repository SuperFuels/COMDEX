import { useEffect, useRef, useState } from 'react';

// ✅ Safely converts NEXT_PUBLIC_API_URL into a proper WebSocket endpoint
function getWssUrl(path: string): string {
  const apiBase = process.env.NEXT_PUBLIC_API_URL || '';

  // Decide WebSocket scheme based on current page protocol
  const wsProtocol =
    typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss' : 'ws';

  // Strip http/https and replace with ws/wss
  let base = apiBase.replace(/^https?:\/\//, `${wsProtocol}://`);

  // Remove trailing /api or /api/
  base = base.replace(/\/api\/?$/, '');

  // Return full WebSocket URL
  return `${base}${path}`;
}

export default function useWebSocket(
  path: string, // e.g. "/ws/codex"
  onMessage: (data: any) => void,
  filterType?: string[] // Optional: only handle matching event types
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