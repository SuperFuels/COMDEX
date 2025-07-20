// File: frontend/hooks/useWebSocket.ts

import { useEffect, useRef, useState } from 'react'

// ✅ Safely transforms NEXT_PUBLIC_API_URL into a WebSocket URL or falls back
function getWssUrl(path: string): string {
  if (typeof window === 'undefined') {
    return '' // SSR-safe
  }

  const wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws'

  const envBase = process.env.NEXT_PUBLIC_API_URL || ''
  const cleanedHost = envBase
    ? envBase
        .replace(/^https?:\/\//, '')      // remove protocol
        .replace(/\/+api\/?$/, '')        // strip /api or /api/
        .replace(/\/+$/, '')              // trailing slash
    : window.location.host                // fallback to current host

  return `${wsProtocol}://${cleanedHost}${path.startsWith('/') ? path : `/${path}`}`
}

export default function useWebSocket(
  path: string, // e.g. "/ws/codex"
  onMessage: (data: any) => void,
  filterType?: string[]
) {
  const socketRef = useRef<WebSocket | null>(null)
  const [connected, setConnected] = useState(false)

  useEffect(() => {
    const url = getWssUrl(path)
    if (!url) {
      console.warn('[WebSocket] Skipping connection — invalid or missing URL.')
      return
    }

    let socket: WebSocket

    try {
      socket = new WebSocket(url)
      socketRef.current = socket
    } catch (err) {
      console.error('[WebSocket] Failed to construct WebSocket:', err)
      return
    }

    socket.onopen = () => {
      console.info(`[WebSocket] Connected to ${url}`)
      setConnected(true)
    }

    socket.onclose = () => {
      console.warn('[WebSocket] Disconnected from', url)
      setConnected(false)
    }

    socket.onerror = (e) => {
      console.error('[WebSocket] Error:', e)
      setConnected(false)
    }

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        const type = data?.type || data?.event
        if (!type || (filterType && !filterType.includes(type))) return
        onMessage(data)
      } catch (err) {
        console.warn('[WebSocket] Invalid JSON message:', err)
      }
    }

    return () => {
      socket?.close()
    }
  }, [path, onMessage, filterType?.join(',')])

  const emit = (event: string, data: any) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ event, ...data }))
    } else {
      console.warn('[WebSocket] Cannot emit — socket not open:', event)
    }
  }

  return {
    socket: socketRef.current,
    connected,
    emit,
  }
}