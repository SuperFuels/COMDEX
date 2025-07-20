// File: frontend/hooks/useWebSocket.ts

import { useEffect, useRef, useState } from 'react'

// ✅ Converts NEXT_PUBLIC_API_URL into a valid WebSocket URL
function getWssUrl(path: string): string {
  const apiBase = process.env.NEXT_PUBLIC_API_URL || ''

  const wsProtocol =
    typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss' : 'ws'

  const base = apiBase
    .replace(/^https?:\/\//, `${wsProtocol}://`)
    .replace(/\/api\/?$/, '') // strip trailing /api if present

  return `${base}${path.startsWith('/') ? path : `/${path}`}`
}

export default function useWebSocket(
  path: string, // e.g., "/ws/codex"
  onMessage: (data: any) => void,
  filterType?: string[]
) {
  const socketRef = useRef<WebSocket | null>(null)
  const [connected, setConnected] = useState(false)

  useEffect(() => {
    const url = getWssUrl(path)
    const socket = new WebSocket(url)
    socketRef.current = socket

    socket.onopen = () => {
      console.info(`[WebSocket] Connected to ${url}`)
      setConnected(true)
    }

    socket.onclose = () => {
      console.warn('[WebSocket] Disconnected')
      setConnected(false)
    }

    socket.onerror = (e) => {
      console.error('[WebSocket] Error:', e)
      setConnected(false)
    }

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)

        const eventType = data?.type || data?.event
        if (!eventType || !onMessage) return
        if (filterType && !filterType.includes(eventType)) return

        onMessage(data)
      } catch (err) {
        console.warn('[WebSocket] Failed to parse message:', err)
      }
    }

    return () => {
      socket.close()
    }
  }, [path, onMessage, filterType?.join(',')])

  const emit = (event: string, data: any) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ event, ...data }))
    } else {
      console.warn('[WebSocket] Cannot emit, socket not open:', event)
    }
  }

  return {
    socket: socketRef.current,
    connected,
    emit,
  }
}