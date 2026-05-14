// server/collab-server.ts
import http, { IncomingMessage } from "http";
import { WebSocketServer } from "ws";
// y-websocket doesn't ship TS types for this path; runtime is fine.
// @ts-ignore
import { setupWSConnection } from "y-websocket/bin/utils";

// Create a plain HTTP server (ws will share this)
const server = http.createServer();

// Create the WebSocket server
const wss = new WebSocketServer({ server });

// Handle WebSocket connections
wss.on("connection", (conn: any, req: IncomingMessage) => {
  try {
    const url = new URL(req.url ?? "/", "http://localhost");
    const room = url.searchParams.get("room") ?? "default";
    setupWSConnection(conn, req, { docName: room, gc: true });
  } catch (err) {
    console.error("❌ WebSocket error:", err);
  }
});

// Bind host/port (from .env or defaults)
const PORT = Number(process.env.COLLAB_PORT ?? 1234);
const HOST = process.env.COLLAB_HOST ?? "0.0.0.0";

server.listen(PORT, HOST, () => {
  console.log(`🔗 Collab server listening on ws://${HOST}:${PORT}`);
});