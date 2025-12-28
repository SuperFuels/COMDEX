// frontend/utils/qfc_websocket_bridge.ts

type QfcUpdatePayload = {
  containerId: string;
  nodes?: any[];
  links?: any[];
  meta?: any;
};

function sameOriginWsUrl(path: string) {
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  return `${proto}://${window.location.host}${path}`;
}

/**
 * Send a single QFC update over WS.
 * ✅ Uses same-origin WS (no direct localhost:8000), so it works in Codespaces/prod.
 *
 * NOTE: This assumes your backend exposes a WS endpoint at /qfc/{containerId}
 * on the same origin (or Vite proxies it). If your real path is different,
 * change WS_PATH below accordingly.
 */
export function broadcast_qfc_update(payload: QfcUpdatePayload) {
  const cid = encodeURIComponent(payload.containerId);

  // If your server expects /qfc/{cid} directly (as before):
  const WS_PATH = `/qfc/${cid}`;

  // If instead you moved WS under /ws/... or /api/ws/...,
  // change it here (example):
  // const WS_PATH = `/api/ws/qfc/${cid}`;

  const socket = new WebSocket(sameOriginWsUrl(WS_PATH));

  socket.onopen = () => {
    try {
      socket.send(
        JSON.stringify({
          type: "qfc_update",
          source: payload.meta?.origin ?? "frontend",
          payload: {
            nodes: payload.nodes ?? [],
            links: payload.links ?? [],
            meta: payload.meta ?? {},
          },
        })
      );
    } finally {
      try {
        socket.close();
      } catch {}
    }
  };

  socket.onerror = (err) => {
    console.error("❌ Failed to send QFC update:", err);
    try {
      socket.close();
    } catch {}
  };
}