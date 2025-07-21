import { useEffect, useRef, useState } from 'react'

function getWssUrl(path: string): string {
  if (typeof window === 'undefined') return ''

  const wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws'

  // Use explicit WebSocket URL if provided
  const rawSocketUrl = process.env.NEXT_PUBLIC_SOCKET_URL
  if (rawSocketUrl) {
    const cleanedHost = rawSocketUrl.replace(/^wss?:\/\//, '').replace(/\/+$/, '')
    const cleanedPath = path.startsWith('/') ? path : `/${path}`
    return `${wsProtocol}://${cleanedHost}${cleanedPath}`
  }

  // Fallback to API URL
  const apiBase = process.env.NEXT_PUBLIC_API_URL || ''
  const cleanedHost =
    apiBase
      .replace(/^https?:\/\//, '')
      .replace(/\/+api\/?$/, '') || window.location.host

  const cleanedPath = path.startsWith('/') ? path : `/${path}`
  return `${wsProtocol}://${cleanedHost}${cleanedPath}`
}

export default function useWebSocket(
  path: string,
  onMessage: (data: any) => void,
  filterType?: string[]
) {
  const socketRef = useRef<WebSocket | null>(null)
  const [connected, setConnected] = useState(false)

  useEffect(() => {
    const url = getWssUrl(path)
    if (!url.startsWith('ws')) {
      console.warn('[WebSocket] Invalid URL:', url)
      return
    }

    const socket = new WebSocket(url)
    socketRef.current = socket

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
        console.warn('[WebSocket] Invalid message:', event.data)
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
      console.warn('[WebSocket] Cannot emit — socket not open:', event)
    }
  }

  return {
    socket: socketRef.current,
    connected,
    emit,
  }
}