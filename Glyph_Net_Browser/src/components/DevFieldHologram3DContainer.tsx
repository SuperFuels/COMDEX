// Glyph_Net_Browser/src/components/DevFieldHologram3DContainer.tsx
'use client';

import React, { useEffect, useRef, useState } from 'react';
import { DevFieldHologram3DScene, GhxPacket } from './DevFieldHologram3D';
import { GHXVisualizerField } from './GHXVisualizerField';

export default function DevFieldHologram3DContainer() {
  const [status, setStatus] = useState<string>('Disconnected');
  const [lastPacket, setLastPacket] = useState<GhxPacket | null>(null);
  const [focusMode, setFocusMode] = useState<'world' | 'focus'>('world');
  const socketRef = useRef<WebSocket | null>(null);

  const toggleFocus = () =>
    setFocusMode((m) => (m === 'world' ? 'focus' : 'world'));

  // cleanup on unmount
  useEffect(() => {
    return () => {
      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, []);

  function connectWs() {
    if (typeof window === 'undefined') return;

    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      return;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const wsUrl = `${protocol}://${window.location.host}/ws/ghx`;
    const ws = new WebSocket(wsUrl);
    socketRef.current = ws;

    setStatus('Connecting to /ws/ghx…');

    ws.onopen = () => setStatus('Connected to /ws/ghx');
    ws.onclose = () => setStatus('Disconnected');
    ws.onerror = () => setStatus('Error on /ws/ghx');

    ws.onmessage = (event) => {
      try {
        const raw = JSON.parse(event.data);
        const packet: GhxPacket = (raw.ghx ?? raw) as GhxPacket;

        if (!packet || !Array.isArray(packet.nodes) || !Array.isArray(packet.edges)) {
          return;
        }

        if (typeof window !== 'undefined') {
          (window as any).__DEVTOOLS_LAST_GHX = packet;
        }

        setLastPacket(packet);
      } catch (e) {
        console.error('DevFieldHologram3DContainer: bad GHX message', e);
      }
    };
  }

  // auto-connect, seed from last hologram, and listen to devtools events
  useEffect(() => {
    connectWs();

    if (typeof window !== 'undefined') {
      const g = (window as any).__DEVTOOLS_LAST_GHX;
      if (g && Array.isArray(g.nodes) && Array.isArray(g.edges)) {
        const seeded: GhxPacket = {
          ghx_version: g.ghx_version ?? '1.0',
          origin: g.origin ?? 'devtools.ast_hologram',
          container_id: g.container_id ?? 'devtools',
          nodes: g.nodes,
          edges: g.edges,
          metadata: g.metadata ?? {},
        };
        setLastPacket(seeded);
      }
    }

    function handleDevGhx(ev: Event) {
      const detail = (ev as CustomEvent).detail;
      if (!detail) return;

      const packet: GhxPacket = (detail.ghx ?? detail) as GhxPacket;
      if (!packet || !Array.isArray(packet.nodes) || !Array.isArray(packet.edges)) {
        return;
      }

      if (typeof window !== 'undefined') {
        (window as any).__DEVTOOLS_LAST_GHX = packet;
      }

      setLastPacket(packet);
    }

    window.addEventListener('devtools.ghx', handleDevGhx as any);
    return () => window.removeEventListener('devtools.ghx', handleDevGhx as any);
  }, []);

  const nodeCount = lastPacket?.nodes?.length ?? 0;
  const edgeCount = lastPacket?.edges?.length ?? 0;
  const origin = lastPacket?.origin ?? '—';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, height: '100%' }}>
      {/* header row */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'baseline',
          fontSize: 12,
        }}
      >
        <div>
          <div style={{ fontWeight: 600 }}>Dev Field Canvas (3D)</div>
          <div style={{ color: '#6b7280' }}>{status}</div>
        </div>

        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <button
            type="button"
            onClick={toggleFocus}
            style={{
              fontSize: 12,
              padding: '4px 10px',
              borderRadius: 999,
              border: '1px solid #e5e7eb',
              background: focusMode === 'focus' ? '#0ea5e9' : '#0f172a',
              color: '#e5e7eb',
              cursor: 'pointer',
            }}
          >
            {focusMode === 'focus' ? '↩︎ Back to Field' : '🔍 Focus Card'}
          </button>

          <button
            type="button"
            onClick={connectWs}
            style={{
              fontSize: 12,
              padding: '4px 10px',
              borderRadius: 999,
              border: '1px solid #e5e7eb',
              background: '#0f172a',
              color: '#e5e7eb',
              cursor: 'pointer',
            }}
          >
            Connect / Reconnect
          </button>
        </div>
      </div>

      {/* main split: field (left) + inspector (right) */}
      <div
        style={{
          flex: 1,
          display: 'flex',
          gap: 12,
          minHeight: 0,
        }}
      >
        {/* 3D field card */}
        <div
          style={{
            flex: 1,
            borderRadius: 12,
            border: '1px solid #020617',
            background: '#020617',
            overflow: 'hidden',
            minHeight: 0,
          }}
        >
          <DevFieldHologram3DScene
            packet={lastPacket}
            focusMode={focusMode}
            onToggleFocus={toggleFocus}
          />
        </div>

        {/* right-hand inspector */}
        <div
          style={{
            width: 320,
            borderRadius: 12,
            border: '1px solid #e5e7eb',
            background: '#f9fafb',
            padding: 12,
            display: 'flex',
            flexDirection: 'column',
            fontSize: 12,
            minHeight: 0,
          }}
        >
          <div style={{ marginBottom: 8 }}>
            <div style={{ fontWeight: 600, marginBottom: 2 }}>Last GHX packet</div>
            {lastPacket ? (
              <div style={{ color: '#6b7280' }}>
                origin: <span style={{ fontFamily: 'monospace' }}>{origin}</span>
                <br />
                nodes: {nodeCount} • edges: {edgeCount}
              </div>
            ) : (
              <div style={{ color: '#6b7280' }}>
                No GHX packets yet. Trigger <b>AST → Hologram</b> or send GHX via{' '}
                <code>/ws/ghx</code>.
              </div>
            )}
          </div>

          {/* tiny 2D GHX sketch */}
          <div style={{ marginBottom: 8 }}>
            <GHXVisualizerField packet={lastPacket} />
          </div>

          <div
            style={{
              flex: 1,
              borderRadius: 8,
              background: '#ffffff',
              border: '1px solid #e5e7eb',
              padding: 8,
              overflow: 'auto',
              fontFamily:
                'SFMono-Regular, ui-monospace, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
              fontSize: 11,
              lineHeight: 1.4,
              whiteSpace: 'pre',
            }}
          >
            {lastPacket
              ? JSON.stringify(lastPacket, null, 2)
              : '// waiting for first GHX packet…'}
          </div>
        </div>
      </div>
    </div>
  );
}