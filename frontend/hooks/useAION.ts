// /workspaces/COMDEX/frontend/hooks/useAION.ts
import { useEffect, useRef, useState } from "react";
import axios from "axios";
import useWebSocket from "./useWebSocket";

type Command = {
  name: string;
  description?: string;
  endpoint?: string;
  stub?: boolean;
};

interface Message {
  role: "user" | "aion" | "system" | "data" | "stub";
  content: string;
  status?: "pending" | "success" | "error";
}

export interface AIONStatus {
  context?: {
    current_container?: string;
    available_containers?: string[];
    [key: string]: any;
  };
  [key: string]: any;
}

function wsBaseFromWindow(): string {
  // same-origin default: ws(s)://<host>
  if (typeof window === "undefined") return "ws://localhost";
  return window.location.origin.replace(/^http/i, "ws");
}

function resolveWsEndpoint(explicit?: string): string {
  // Priority:
  // 1) explicit url
  // 2) envs (vite/next)
  // 3) same-origin "/ws"
  const envUrl =
    (typeof import.meta !== "undefined" && (import.meta as any).env?.VITE_WS_URL) ||
    (typeof process !== "undefined" && (process.env as any).NEXT_PUBLIC_WS_URL);

  const raw = explicit || envUrl || `${wsBaseFromWindow()}/ws`;

  // convert http(s) -> ws(s)
  if (/^https?:\/\//i.test(raw)) return raw.replace(/^http/i, "ws");
  // already ws(s)
  if (/^wss?:\/\//i.test(raw)) return raw;

  // relative "/ws" style
  const base = wsBaseFromWindow();
  const path = raw.startsWith("/") ? raw : `/${raw}`;
  return `${base}${path}`;
}

export default function useAION(side: "left" | "right", label: string = "AION Terminal") {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [tokenUsage, setTokenUsage] = useState<number | null>(null);
  const [availableCommands, setAvailableCommands] = useState<Command[]>([]);
  const [status, setStatus] = useState<any>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const append = (role: Message["role"], content: string, status?: Message["status"]) => {
    setMessages((prev) => [...prev, { role, content, status }]);
  };

  const syncMessagesToBackend = async () => {
    try {
      await axios.post("/aion/sync-messages", { messages });
    } catch (err: any) {
      append("system", `⚠️ Failed to sync messages: ${err.message}`, "error");
    }
  };

  const sendPrompt = async () => {
    if (!input.trim()) return;
    append("user", input, "pending");
    setLoading(true);

    try {
      const res = await axios.post(`/aion/prompt`, { prompt: input });
      const reply = res.data.reply || "(no response)";
      const tokens = res.data.tokens_used;
      const cost = res.data.cost_estimate;

      if (tokens) setTokenUsage(tokens);

      let formatted = reply;
      if (tokens || cost) {
        formatted += `\n\n🧮 Tokens used: ${tokens || "N/A"}\n💸 Estimated cost: $${cost || "N/A"}`;
      }

      append("aion", formatted, "success");
      await syncMessagesToBackend();
    } catch (err: any) {
      append("system", `❌ AION error: ${err.message}`, "error");
    }

    setLoading(false);
    setInput("");
  };

  const sendCommand = async (command: string) => {
    if (!command.trim()) return;
    append("user", command, "pending");
    setLoading(true);

    try {
      const res = await axios.post("/aion/command", {
        command,
        side,
        label,
      });

      const { message, output, error, stub } = res.data;

      if (error) {
        append("system", `❌ ${error}`, "error");
      } else if (stub) {
        append("stub", message || `🛠️ Stub command "${command}"`, "success");
      } else if (output) {
        append("data", `📤 ${output}`, "success");
      } else {
        append("aion", message || `✅ ${label || command} completed.`, "success");
      }

      await syncMessagesToBackend();
    } catch (err: any) {
      append("system", `❌ Command failed: ${err.message}`, "error");
    }

    setLoading(false);
    setInput("");
  };

  const callEndpoint = async (
    endpoint: string,
    labelText: string,
    method: "get" | "post" = "post"
  ) => {
    append("system", `📡 Fetching ${labelText}...`, "pending");

    if (endpoint.startsWith("stub:")) {
      append("stub", `🛠️ Stub command '${labelText}' not yet implemented.`, "success");
      return;
    }

    try {
      const url = `/aion/${endpoint.replace(/^\/+/, "")}`;
      const res = method === "post" ? await axios.post(url) : await axios.get(url);
      const data = res.data;

      if (data.tokens_used) setTokenUsage(data.tokens_used);

      let formatted =
        typeof data === "object" ? JSON.stringify(data, null, 2) : String(data);

      if (data.tokens_used || data.cost_estimate) {
        formatted += `\n\n🧮 Tokens used: ${data.tokens_used || "N/A"}\n💸 Estimated cost: $${data.cost_estimate || "N/A"}`;
      }

      append("aion", `✅ ${labelText}:\n${formatted}`, "success");
    } catch (err: any) {
      append("system", `❌ ${labelText} error: ${err.message}`, "error");
    }
  };

  const sendInitialPrompt = async () => {
    const prompt = "Provide me with an update on your overall progress & how you are feeling.";
    append("user", prompt, "pending");
    try {
      const res = await axios.post(`/aion/prompt`, { prompt });

      const reply = res.data.reply || "(no response)";
      const tokens = res.data.tokens_used;
      const cost = res.data.cost_estimate;

      if (tokens) setTokenUsage(tokens);

      let formatted = reply;
      if (tokens || cost) {
        formatted += `\n\n🧮 Tokens used: ${tokens || "N/A"}\n💸 Estimated cost: $${cost || "N/A"}`;
      }

      append("aion", formatted, "success");
      await syncMessagesToBackend();
    } catch (err: any) {
      append("system", `❌ Startup failed: ${err.message}`, "error");
    }
  };

  const fetchCommandRegistry = async () => {
    try {
      const res = await axios.get("/aion/command/registry");
      const commands = res.data.commands || [];
      setAvailableCommands(commands);
    } catch (err: any) {
      append("system", `⚠️ Failed to load command list: ${err.message}`, "error");
    }
  };

  const fetchStatus = async () => {
    try {
      const res = await axios.get("/aion/status");
      setStatus(res.data);
    } catch (err: any) {
      append("system", `⚠️ Failed to fetch status: ${err.message}`, "error");
    }
  };

  // ✅ WebSocket: same-origin by default (no hardcoded localhost:8000)
  const wsUrl = resolveWsEndpoint();

  useWebSocket(
    wsUrl,
    (msg: any) => {
      if (msg?.event === "status_update" && msg.context) {
        setStatus((prev: any) => ({
          ...prev,
          context: {
            ...prev?.context,
            ...msg.context,
          },
        }));
      }

      if (msg?.event === "glyph_update" && side === "right") {
        append("data", "🧬 Glyphs updated from WebSocket.", "success");
      }

      if (msg?.event === "container_teleport") {
        append("system", `🧭 Teleported to: ${msg.containerId}`, "success");
      }
    },
    ["status_update", "glyph_update", "container_teleport"]
  );

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    const boot = async () => {
      if (side === "left") {
        append("system", "🟢 Booting AION Terminal...", "success");
        await fetchCommandRegistry();
        await fetchStatus();
        await sendInitialPrompt();
      }
    };
    boot();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [side]);

  return {
    input,
    setInput,
    loading,
    messages,
    setMessages,
    sendPrompt,
    callEndpoint,
    sendCommand,
    bottomRef,
    tokenUsage,
    availableCommands,
    setAvailableCommands,
    status,
    setStatus,
  };
}