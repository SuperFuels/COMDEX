// File: frontend/hooks/useWebSocket.ts

import { useEffect, useRef, useState } from 'react'

// ✅ Cleanly transforms NEXT_PUBLIC_API_URL into a valid WebSocket URL
function getWssUrl(path: string): string {
  const apiBase = process.env.NEXT_PUBLIC_API_URL || ''

  const wsProtocol =
    typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss' : 'ws'

  const cleanedHost = apiBase
    .replace(/^https?:\/\//, '')       // remove protocol
    .replace(/\/+api\/?$/, '')         // remove trailing /api or /api/
    .replace(/\/+$/, '')               // remove trailing slash if any

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
    let socket: WebSocket

    try {
      socket = new WebSocket(url)
      socketRef.current = socket
    } catch (err) {
      console.error('[WebSocket] Failed to construct:', err)
      return
    }

    socket.onopen = () => {
      console.info(`[WebSocket] Connected: ${url}`)
      setConnected(true)
    }

    socket.onclose = () => {
      console.warn('[WebSocket] Disconnected:', url)
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
        console.warn('[WebSocket] Invalid JSON:', err)
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
      console.warn('[WebSocket] Cannot emit, not open:', event)
    }
  }

  return {
    socket: socketRef.current,
    connected,
    emit,
  }
}