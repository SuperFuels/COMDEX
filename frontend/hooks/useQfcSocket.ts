import { useEffect } from "react";
import { io, Socket } from "socket.io-client";

let socket: Socket;

export const useQfcSocket = (containerId: string, onUpdate: (payload: any) => void) => {
  useEffect(() => {
    if (!containerId) return;

    socket = io();
    socket.emit("join-container", containerId);

    socket.on("qfc-sync", onUpdate);

    return () => {
      socket.disconnect();
    };
  }, [containerId]);
};