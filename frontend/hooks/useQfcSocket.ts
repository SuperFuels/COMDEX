// File: frontend/hooks/useQfcSocket.ts
'use client';

import { useEffect, useRef } from 'react';

export const useQfcSocket = (
  containerId: string,
  onUpdate: (payload: any) => void
) => {
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!containerId) return;

    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const url = `${proto}://${window.location.host}/api/qfc?container_id=${encodeURIComponent(
      containerId
    )}`;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      // Back-compat with the old socket.io "join-container" emit
      try {
        ws.send(JSON.stringify({ event: 'join-container', payload: containerId }));
      } catch {}
    };

    ws.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data);
        // Prefer structured { event, payload } messages
        if (msg && typeof msg === 'object' && 'event' in msg) {
          if (msg.event === 'qfc-sync') onUpdate(msg.payload);
          else onUpdate(msg.payload ?? msg);
        } else {
          onUpdate(msg);
        }
      } catch {
        // Fallback: server sent plain text / raw payload
        onUpdate(evt.data);
      }
    };

    ws.onerror = () => {
      // no-op; optionally add logging
    };

    ws.onclose = () => {
      wsRef.current = null;
    };

    return () => {
      ws.close();
    };
  }, [containerId, onUpdate]);
};