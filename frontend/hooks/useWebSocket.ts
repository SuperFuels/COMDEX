// frontend/hooks/useWebSocket.ts
import { useEffect, useRef, useState } from 'react';

export default function useWebSocket(
  url: string,
  onMessage: (data: any) => void,
  filterEvent?: string[] // optional: only listen to specific events like ['glyph_update']
) {
  const socketRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const socket = new WebSocket(url);
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
  }, [url, onMessage, filterEvent?.join(',')]);

  // 🎯 New emit method using the open socket
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
    emit, // 💡 expose emit function here
  };
}