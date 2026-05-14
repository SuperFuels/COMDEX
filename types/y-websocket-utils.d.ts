// Minimal client types — enough for our hook usage
declare module "y-websocket" {
  export class WebsocketProvider {
    constructor(
      url: string,
      room: string,
      doc: any,
      opts?: {
        connect?: boolean;
        params?: Record<string, string>;
        WebSocketPolyfill?: any;
      }
    );
    connect(): void;
    disconnect(): void;
    awareness: any;
    wsconnected: boolean;
    wsconnecting: boolean;
  }
}

// Your original server-side utils declaration
declare module "y-websocket/bin/utils" {
  import type { IncomingMessage } from "http";
  import type WebSocket from "ws";

  export function setupWSConnection(
    conn: WebSocket,
    req: IncomingMessage,
    opts?: { docName?: string; gc?: boolean }
  ): void;
}