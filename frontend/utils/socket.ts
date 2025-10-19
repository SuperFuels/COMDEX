// frontend/utils/socket.ts
// ======================================================
// 🔌 Universal WebSocket client (local + Vercel)
// ======================================================

// Safe lazy initialization
let socket: WebSocket | null = null;
const listeners: Array<(msg: any) => void> = [];

// Resolve WebSocket URL
function resolveSocketURL(): string {
  // 1️⃣ Use environment variable if defined (Vercel)
  const envURL = process.env.NEXT_PUBLIC_SOCKET_URL || process.env.NEXT_PUBLIC_WS_URL;
  if (envURL) return envURL;

  // 2️⃣ Fallback to browser host (local dev)
  if (typeof window !== 'undefined') {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${window.location.host}/ws/containers`;
  }

  // 3️⃣ SSR safety
  return '';
}

// Initialize on client
if (typeof window !== 'undefined') {
  const wsURL = resolveSocketURL();

  try {
    socket = new WebSocket(wsURL);
    console.log(`🌐 WebSocket connecting to: ${wsURL}`);

    socket.addEventListener('open', () => console.log('✅ WebSocket connection opened.'));
    socket.addEventListener('close', () => console.warn('🔌 WebSocket connection closed.'));
    socket.addEventListener('error', (err) => console.error('❌ WebSocket error:', err));

    socket.addEventListener('message', (event) => {
      try {
        const msg = JSON.parse(event.data);
        for (const listener of listeners) listener(msg);
      } catch (err) {
        console.error('❌ WebSocket message error:', err);
      }
    });
  } catch (err) {
    console.error('⚠️ WebSocket initialization failed:', err);
  }
}

// Public API
export const addWebSocketListener = (cb: (msg: any) => void) => listeners.push(cb);
export const removeWebSocketListener = (cb: (msg: any) => void) => {
  const i = listeners.indexOf(cb);
  if (i !== -1) listeners.splice(i, 1);
};
export const getSocket = () => socket;
export default socket;