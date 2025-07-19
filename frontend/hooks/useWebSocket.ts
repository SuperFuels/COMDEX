// frontend/hooks/useWebSocket.ts
import { useEffect, useRef, useState } from 'react';

// ✅ Helper to convert API base URL to WSS endpoint
function getWssUrl(path: string): string {
  const base = process.env.NEXT_PUBLIC_API_URL || '';
  return base.replace(/^http/, 'wss').replace(/\/api$/, '') + path;
}

export default function useWebSocket(
  path: string, // expects relative WebSocket path like "/ws/containers"
  onMessage: (data: any) => void,
  filterEvent?: string[] // optional: only listen to specific events like ['glyph_update']
) {
  const socketRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const fullUrl = getWssUrl(path);
    const socket = new WebSocket(fullUrl);
    socketRef.current = socket;

    socket.onopen = () => setConnected(true);
    socket.onclose = () => setConnected(false);
    socket.onerror = () => setConnected(false);

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (!data?.event || !onMessage) return;
        if (filterEvent && !filterEvent.includes(data.event)) return;

        onMessage(data);
      } catch (err) {
        console.warn('WebSocket parse error', err);
      }
    };

    return () => {
      socket.close();
    };
  }, [path, onMessage, filterEvent?.join(',')]);

  const emit = (event: string, data: any) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ event, data }));
    } else {
      console.warn('WebSocket not connected, cannot emit event:', event);
    }
  };

  return {
    socket: socketRef.current,
    connected,
    emit,
  };
}