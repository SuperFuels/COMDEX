// ✅ utils/qfc_websocket_bridge.ts (frontend)

type QfcUpdatePayload = {
  containerId: string;
  nodes?: any[];
  links?: any[];
  meta?: any;
};

export function broadcast_qfc_update(payload: QfcUpdatePayload) {
  const socket = new WebSocket(`ws://localhost:8000/qfc/${payload.containerId}`);

  socket.onopen = () => {
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
    socket.close();
  };

  socket.onerror = (err) => {
    console.error("❌ Failed to send QFC update:", err);
  };
}