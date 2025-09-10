// ✅ WebSocket handler for QFC sync
import { NextApiRequest } from "next";
import { NextApiResponseServerIO } from "@/types/next";
import { Server } from "socket.io";

export default function handler(req: NextApiRequest, res: NextApiResponseServerIO) {
  if (!res.socket.server.io) {
    console.log("🧠 Initializing QFC WS server...");
    const io = new Server(res.socket.server);
    res.socket.server.io = io;

    io.on("connection", (socket) => {
      socket.on("join-container", (containerId) => {
        socket.join(containerId);
      });

      socket.on("qfc-update", ({ containerId, payload }) => {
        socket.to(containerId).emit("qfc-sync", payload);
      });
    });
  }
  res.end();
}