// /src/App.tsx
import { useEffect, useState } from "react";
import TopBar from "./components/TopBar";
import Sidebar from "./components/Sidebar";
import WaveInbox from "./components/WaveInbox";
import KGDock from "./components/KGDock";
import ContainerView from "./components/ContainerView";
import { parseAddress } from "./lib/nav/parse";
import { routeNav } from "./lib/nav/router";
import WaveOutbox from "./components/WaveOutbox";
import ChatThread from "./routes/ChatThread";

type Mode = "wormhole" | "http";
type NavArg = string | { mode: Mode; address: string };

// include "chat" in the app’s local view state
type ActiveTab = "home" | "inbox" | "outbox" | "kg" | "settings" | "chat";

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [showWaves, setShowWaves] = useState(false);
  const [active, setActive] = useState<ActiveTab>("home");
  const [wavesCount, setWavesCount] = useState(1);

  // hash-derived props we pass down
  const [inboxTopicFromHash, setInboxTopicFromHash] = useState<string>("");
  const [chatTopicFromHash, setChatTopicFromHash] = useState<string>("");
  const [chatKGFromHash, setChatKGFromHash] = useState<"personal" | "work" | undefined>(undefined);

  // helpers to read hash params
  const readTopicFromHash = (h: string): string => {
    try {
      const u = new URL(h.replace("#", "http://x"));
      return u.searchParams.get("topic") || "";
    } catch {
      return "";
    }
  };
  const readKGFromHash = (h: string): "personal" | "work" => {
    try {
      const u = new URL(h.replace("#", "http://x"));
      const kg = (u.searchParams.get("kg") || "personal").toLowerCase();
      return kg === "work" ? "work" : "personal";
    } catch {
      return "personal";
    }
  };

  // react to hash changes (and set page title)
  useEffect(() => {
    const onHash = () => {
      const h = window.location.hash || "";

      if (h.startsWith("#/chat")) {
        setActive("chat");
        setChatTopicFromHash(readTopicFromHash(h));
        setChatKGFromHash(readKGFromHash(h));
        document.title = `Chat — Glyph Net`;
        return;
      }

      if (h.startsWith("#/inbox")) {
        setActive("inbox");
        setInboxTopicFromHash(readTopicFromHash(h));
        document.title = `Inbox — Glyph Net`;
        return;
      }

      if (h.startsWith("#/outbox")) {
        setActive("outbox");
        document.title = `Outbox — Glyph Net`;
        return;
      }

      if (h.startsWith("#/wormhole/")) {
        document.title = `🌀 ${decodeURIComponent(h.split("/").pop() || "")} — Glyph Net`;
        return;
      }

      if (h.startsWith("#/dimension/")) {
        document.title = `Dimension — Glyph Net`;
        return;
      }

      if (h.startsWith("#/container/")) {
        const name = decodeURIComponent(h.split("/").pop() || "");
        document.title = `${name} — Container • Glyph Net`;
        return;
      }

      document.title = `Glyph Net`;
    };

    window.addEventListener("hashchange", onHash);
    onHash(); // initial
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  // waves counter badge
  useEffect(() => {
    const onWave = () => setWavesCount((n) => n + 1);
    window.addEventListener("glyphnet:wave", onWave as EventListener);
    return () => window.removeEventListener("glyphnet:wave", onWave as EventListener);
  }, []);

  // Wormhole resolution logging (unchanged)
  useEffect(() => {
    const onResolved = (e: Event) => {
      const rec = (e as CustomEvent).detail;
      console.log("🔗 Wormhole resolved:", rec);
    };
    const onError = (e: Event) => {
      const { name, error } = (e as CustomEvent).detail;
      console.warn("⚠️ Wormhole resolve failed:", name, error);
    };
    window.addEventListener("wormhole:resolved", onResolved as EventListener);
    window.addEventListener("wormhole:resolve_error", onError as EventListener);
    return () => {
      window.removeEventListener("wormhole:resolved", onResolved as EventListener);
      window.removeEventListener("wormhole:resolve_error", onError as EventListener);
    };
  }, []);

  // Accept both a string or an object from TopBar
  const handleNavigate = (arg: NavArg) => {
    const address = typeof arg === "string" ? arg : arg.address;
    routeNav(parseAddress(address));
  };

  // Sidebar still only knows about: "home" | "inbox" | "outbox" | "kg" | "settings".
  // Map "chat" -> "inbox" for highlighting.
  const sidebarActive: "home" | "inbox" | "outbox" | "kg" | "settings" =
    active === "chat" ? "inbox" : (active as any);

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column" }}>
      <TopBar
        onNavigate={handleNavigate}
        onOpenSidebar={() => setSidebarOpen(true)}
        onAskAion={() => alert("AION panel will open here.")}
        onConnectWallet={() => alert("Wallet connect flow goes here.")}
        onToggleWaves={() => setShowWaves((v) => !v)}
        wavesCount={wavesCount}
      />

      {/* overlay sidebar — completely hidden when closed */}
      <Sidebar
        open={sidebarOpen}
        active={sidebarActive}
        onSelect={(id) => setActive((id as unknown) as Exclude<ActiveTab, "chat">)}
        onClose={() => setSidebarOpen(false)}
      />

      {/* main content */}
      <main style={{ flex: 1, padding: 16, background: "#f8fafc", overflow: "auto" }}>
        {active === "home" && (
          <>
            <h1>Glyph Net</h1>
            <p>
              Send your first wave <code>www.tessaris.tp</code>.
            </p>
          </>
        )}

        {/* Views */}
        {active === "chat" ? (
          // New consolidated chat experience renders its own left Recents rail + right Chat pane
          <div style={{ height: "calc(100vh - 96px)" /* approx topbar+padding */ }}>
            <ChatThread
              defaultTopic={chatTopicFromHash || "ucs://local/ucs_hub"}
              defaultGraph={chatKGFromHash}
            />
          </div>
        ) : active === "inbox" ? (
          <WaveInbox defaultTopic={inboxTopicFromHash || "ucs://local/ucs_hub"} />
        ) : active === "kg" ? (
          <KGDock />
        ) : active === "outbox" ? (
          <WaveOutbox />
        ) : active === "settings" ? (
          <p>Settings (stub)</p>
        ) : window.location.hash.startsWith("#/container/") ? (
          <ContainerView />
        ) : (
          <div
            style={{
              padding: 12,
              border: "1px solid #e5e7eb",
              borderRadius: 8,
              background: "#fff",
            }}
          >
            <strong>AION:</strong> ready (UI stub). This pane becomes the agent console / GlyphGrid.
          </div>
        )}
      </main>

      {/* Waves slide-over */}
      {showWaves && (
        <div
          style={{
            position: "fixed",
            top: 64,
            right: 16,
            width: 360,
            height: "70vh",
            background: "#fff",
            border: "1px solid #e5e7eb",
            borderRadius: 12,
            boxShadow: "0 10px 30px rgba(0,0,0,.12)",
            overflow: "hidden",
            zIndex: 50,
          }}
        >
          <WaveInbox />
        </div>
      )}
    </div>
  );
}