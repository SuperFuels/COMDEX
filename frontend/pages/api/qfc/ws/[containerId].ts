// pages/api/qfc/ws/[containerId].ts
// ✅ Node Runtime API route that attaches a single Socket.IO server instance
import type { NextApiRequest, NextApiResponse } from "next";

// Tell Next not to parse the body (Socket.IO upgrades the request)
export const config = {
  api: { bodyParser: false },
};

// Minimal extension to carry an `io` instance on the HTTP server
type NextApiResponseWithSocket = NextApiResponse & {
  socket: NextApiResponse["socket"] & {
    server: { io?: any };
  };
};

export default function handler(req: NextApiRequest, res: NextApiResponseWithSocket) {
  // Lazily create the Socket.IO server once per server instance
  if (!res.socket.server.io) {
    // Lazy require keeps TS happy and avoids importing types at the top level
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const { Server } = require("socket.io");

    const io = new Server(res.socket.server, {
      // Optional: customize the path if you like
      path: "/api/qfc/ws/socket.io",
      addTrailingSlash: false,
      transports: ["websocket"], // stick to ws in serverless envs
    });

    res.socket.server.io = io;

    io.on("connection", (socket: any) => {
      // Join a room for a specific container
      socket.on("join-container", (containerId: string) => {
        if (typeof containerId === "string" && containerId.length > 0) {
          socket.join(containerId);
        }
      });

      // Broadcast QFC updates to peers in that container room
      socket.on(
        "qfc-update",
        (msg: { containerId: string; payload: unknown }) => {
          const { containerId, payload } = msg || ({} as any);
          if (typeof containerId === "string" && containerId.length > 0) {
            socket.to(containerId).emit("qfc-sync", payload);
          }
        }
      );
    });

    // Optional: log for visibility in dev
    // console.log("🧠 QFC Socket.IO server initialized");
  }

  // This API route only establishes the socket server
  res.end();
}