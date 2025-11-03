// /src/App.tsx
import { useEffect, useState } from "react";
import TopBar from "./components/TopBar";
import Sidebar from "./components/Sidebar";
import WaveInbox from "./components/WaveInbox";
import KGDock from "./components/KGDock";
import ContainerView from "./components/ContainerView";
import { parseAddress } from "./lib/nav/parse";
import { routeNav } from "./lib/nav/router";

type Mode = "wormhole" | "http";

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [showWaves, setShowWaves] = useState(false);
  const [active, setActive] =
    useState<"home" | "inbox" | "outbox" | "kg" | "settings">("home");
  const [wavesCount, setWavesCount] = useState(1);

  // Title updates on hash changes
  useEffect(() => {
    const onHash = () => {
      const h = location.hash;
      if (h.startsWith("#/wormhole/")) {
        document.title = `🌀 ${decodeURIComponent(h.split("/").pop() || "")} — Glyph Net`;
      } else if (h.startsWith("#/dimension/")) {
        document.title = `Dimension — Glyph Net`;
      } else if (h.startsWith("#/container/")) {
        const name = decodeURIComponent(h.split("/").pop() || "");
        document.title = `${name} — Container • Glyph Net`;
      }
    };
    window.addEventListener("hashchange", onHash);
    onHash(); // initial
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  // ✅ Listen for wormhole resolution events from router.ts
  useEffect(() => {
    const onResolved = (e: Event) => {
      const rec = (e as CustomEvent).detail;
      console.log("🔗 Wormhole resolved:", rec); // rec.address, rec.to, rec.container, rec.meta
      // TODO: set state / open ContainerView / connect WS
      // Example: window.location.hash = `#/container/${encodeURIComponent(rec.to)}`;
    };
    const onError = (e: Event) => {
      const { name, error } = (e as CustomEvent).detail;
      console.warn("⚠️ Wormhole resolve failed:", name, error);
    };
    window.addEventListener("wormhole:resolved", onResolved as any);
    window.addEventListener("wormhole:resolve_error", onError as any);
    return () => {
      window.removeEventListener("wormhole:resolved", onResolved as any);
      window.removeEventListener("wormhole:resolve_error", onError as any);
    };
  }, []);

  const handleNavigate = ({ address }: { mode: Mode; address: string }) => {
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
            <h1>Glyph_Net_Browser — Alpha Shell</h1>
            <p>
              Home: your personal container (AION entry). Try <code>nike</code> or{" "}
              <code>www.wikipedia.org</code>.
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
              <WaveInbox />
            ) : active === "kg" ? (
              <KGDock />
            ) : active === "outbox" ? (
              <div>
                <h3 style={{ margin: "10px 0" }}>Wave Outbox</h3>
                <p>No pending sends.</p>
              </div>
            ) : active === "settings" ? (
              <p>Settings (stub)</p>
            ) : location.hash.startsWith("#/container/") ? (
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