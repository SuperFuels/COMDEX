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

type Mode = "wormhole" | "http";
type NavArg = string | { mode: Mode; address: string };

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [showWaves, setShowWaves] = useState(false);
  const [active, setActive] =
    useState<"home" | "inbox" | "outbox" | "kg" | "settings">("home");
  const [wavesCount, setWavesCount] = useState(1);

  // ✅ SSR-safe topic from hash (?topic=...)
  const topicFromHash = (() => {
    if (typeof window === "undefined" || typeof window.location === "undefined") return "";
    const h = window.location.hash || "";
    if (!h.startsWith("#/inbox")) return "";
    const u = new URL(h.replace("#", "http://x"));
    return u.searchParams.get("topic") || "";
  })();

  // Title + active tab from hash
  useEffect(() => {
    const onHash = () => {
      const h = window.location.hash || "";
      if (h.startsWith("#/inbox")) {
        setActive("inbox");
        document.title = `Inbox — Glyph Net`;
      } else if (h.startsWith("#/outbox")) {
        setActive("outbox");
        document.title = `Outbox — Glyph Net`;
      } else if (h.startsWith("#/wormhole/")) {
        document.title = `🌀 ${decodeURIComponent(h.split("/").pop() || "")} — Glyph Net`;
      } else if (h.startsWith("#/dimension/")) {
        document.title = `Dimension — Glyph Net`;
      } else if (h.startsWith("#/container/")) {
        const name = decodeURIComponent(h.split("/").pop() || "");
        document.title = `${name} — Container • Glyph Net`;
      } else {
        document.title = `Glyph Net`;
      }
    };
    window.addEventListener("hashchange", onHash);
    onHash(); // initial
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  // Bubble from WaveInbox to increment waves badge
  useEffect(() => {
    const onWave = () => setWavesCount((n) => n + 1);
    window.addEventListener("glyphnet:wave", onWave as EventListener);
    return () => window.removeEventListener("glyphnet:wave", onWave as EventListener);
  }, []);

  // Wormhole resolution logging
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

  // ✅ Accept both a string or an object from TopBar
  const handleNavigate = (arg: NavArg) => {
    const address = typeof arg === "string" ? arg : arg.address;
    routeNav(parseAddress(address));
  };

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
        active={active}
        onSelect={(id) => setActive(id)}
        onClose={() => setSidebarOpen(false)}
      />

      {/* main content always full width */}
      <main style={{ flex: 1, padding: 16, background: "#f8fafc", overflow: "auto" }}>
        {active === "home" && (
          <>
            <h1>Glyph Net</h1>
            <p>
              Send your first wave <code>www.tessaris.tp</code>.
            </p>
          </>
        )}

        {/* center content + KG side dock */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 320px",
            gap: 12,
            marginTop: 12,
          }}
        >
          <div style={{ minWidth: 0 }}>
            {active === "inbox" ? (
              <WaveInbox defaultTopic={topicFromHash || "ucs://local/ucs_hub"} />
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
                <strong>AION:</strong> ready (UI stub). This pane becomes the agent
                console / GlyphGrid.
              </div>
            )}
          </div>

          {/* NOTE: This shows KGDock always on the right. If you don't want two KGDocks
              when active === "kg", wrap this with `active !== "kg" && <KGDock />`. */}
          <div>
            <KGDock />
          </div>
        </div>
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