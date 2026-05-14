// File: frontend/utils/ws.ts

let socket: WebSocket | null = null

type Callback = (data: any) => void

let onMessageCallback: Callback | null = null

export function connectWebSocket(onMessage: Callback) {
  if (socket && socket.readyState === WebSocket.OPEN) return

  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
  const host = window.location.host
  const wsUrl = `${protocol}://${host}/ws/containers`

  socket = new WebSocket(wsUrl)
  onMessageCallback = onMessage

  socket.onopen = () => {
    console.log('[🔌] WebSocket connected')
  }

  socket.onmessage = (event) => {
    const data = JSON.parse(event.data)
    if (onMessageCallback) onMessageCallback(data)
  }

  socket.onclose = () => {
    console.warn('[⚠️] WebSocket closed. Attempting to reconnect in 3s...')
    setTimeout(() => connectWebSocket(onMessageCallback!), 3000)
  }

  socket.onerror = (err) => {
    console.error('[❌] WebSocket error:', err)
    socket?.close()
  }
}
