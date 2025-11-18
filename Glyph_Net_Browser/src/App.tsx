// src/App.tsx
import { useEffect, useRef, useState } from "react";
import TopBar, { RadioStatus } from "./components/TopBar";
import Sidebar from "./components/Sidebar";
import WaveInbox from "./components/WaveInbox";
import KGDock from "./components/KGDock";
import ContainerView from "./components/ContainerView";
import WaveOutbox from "./components/WaveOutbox";
import ChatThread from "./routes/ChatThread";
import BridgePanel from "./routes/BridgePanel";
import { parseAddress } from "./lib/nav/parse";
import { routeNav } from "./lib/nav/router";
import { useRadioHealth } from "./hooks/useRadioHealth";
import { KG_API_BASE } from "./utils/kgApiBase";
import { OWNER_WA } from "./lib/constants";

type Mode = "wormhole" | "http";
type NavArg = string | { mode: Mode; address: string };
type ActiveTab = "home" | "inbox" | "outbox" | "kg" | "settings" | "chat" | "bridge";

type Session = { slug: string; wa: string } | null;

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [showWaves, setShowWaves] = useState(false);
  const [active, setActive] = useState<ActiveTab>("home");
  const [wavesCount, setWavesCount] = useState(1);

  const [inboxTopicFromHash, setInboxTopicFromHash] = useState<string>("");
  const [chatTopicFromHash, setChatTopicFromHash] = useState<string>("");
  const [chatKGFromHash, setChatKGFromHash] = useState<"personal" | "work" | undefined>(undefined);

  // --- session (inline, no extra hook) ---
  const [session, setSession] = useState<Session>(null);
  const [sessionLoading, setSessionLoading] = useState<boolean>(true);

  const refreshSession = () => {
    setSessionLoading(true);
    fetch("/api/session/me")
      .then((r) => (r.ok ? r.json() : null))
      .then((j) => {
        const s: Session = j?.session ? { slug: j.session.slug, wa: j.session.wa } : null;
        setSession(s);
        setSessionLoading(false);
      })
      .catch(() => {
        setSession(null);
        setSessionLoading(false);
      });
  };

  const logout = () => {
    fetch("/api/session/clear", { method: "POST" }).catch(() => {});
    localStorage.removeItem("gnet:user_slug");
    localStorage.removeItem("gnet:wa");
    setSession(null);
    if (location.hash.startsWith("#/container/")) {
      location.hash = "#/";
    }
  };

  useEffect(() => {
    refreshSession();
  }, []);

  // Keep localStorage in sync + optionally auto-open home once
  useEffect(() => {
    if (session?.slug) {
      localStorage.setItem("gnet:user_slug", session.slug);
      localStorage.setItem("gnet:wa", session.wa);
      localStorage.setItem("gnet:ownerWa", session.wa); // ← NEW: canonical owner

      if (!location.hash || location.hash === "#/" || location.hash === "#") {
        window.location.hash = `#/container/${session.slug}__home`;
      }
    } else {
      localStorage.removeItem("gnet:user_slug");
      localStorage.removeItem("gnet:wa");
      localStorage.removeItem("gnet:ownerWa"); // ← NEW: clear on logout
    }
  }, [session]);

  // --- radio health ---
  const [radioStatus, setRadioStatus] = useState<RadioStatus>("unknown");
  const [healthyAt, setHealthyAt] = useState<number>(0);
  const healthRef = useRef<ReturnType<typeof useRadioHealth> | null>(null);

  useEffect(() => {
    const h = useRadioHealth({ onRecovered: () => setHealthyAt(Date.now()) });
    healthRef.current = h;
    setRadioStatus(h.status);
    const unsub = h.subscribe(setRadioStatus);
    return () => {
      unsub();
      h.dispose();
    };
  }, []);

  const showToast = healthyAt > 0 && Date.now() - healthyAt < 4000;

  // helpers to read hash params
  const readTopicFromHash = (hash: string): string => {
    try {
      const u = new URL(hash.replace("#", "http://x"));
      return u.searchParams.get("topic") || "";
    } catch {
      return "";
    }
  };
  const readKGFromHash = (hash: string): "personal" | "work" => {
    try {
      const u = new URL(hash.replace("#", "http://x"));
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

      if (h.startsWith("#/bridge")) {
        setActive("bridge");
        document.title = `RF Bridge — Glyph Net`;
        return;
      }

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
        setActive("settings"); // legacy bucket
        document.title = `Dimension — Glyph Net`;
        return;
      }

      if (h.startsWith("#/container/")) {
        const name = decodeURIComponent(h.split("/").pop() || "");
        setActive("home");
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

  // KG visit/dwell journaling via UMD (/public/js/kg_emit.js)
  useEffect(() => {
    const ownerWa =
      session?.wa ||
      localStorage.getItem("gnet:ownerWa") ||
      OWNER_WA;

    const kgEmit = (window as any).KGEmit;
    if (!kgEmit || typeof kgEmit.initVisitEmitters !== "function") {
      // UMD not loaded yet or no initVisitEmitters; nothing to do
      return;
    }

    const stop = kgEmit.initVisitEmitters({
      apiBase: KG_API_BASE,
      ownerWa,
      getGraph: () => {
        try {
          return readKGFromHash(window.location.hash || "#/"); // "personal" | "work"
        } catch {
          return "personal";
        }
      },
      getTopic: () => {
        try {
          return readTopicFromHash(window.location.hash || "#/") || "ucs://local/ucs_hub";
        } catch {
          return "";
        }
      },
      getPath: () => window.location.hash || "#/",
    });

    // allow UMD helper to clean up listeners/timers
    return () => {
      if (typeof stop === "function") stop();
    };
  }, [session?.wa]);

  // Accept both a string or an object from TopBar
  const handleNavigate = (arg: NavArg) => {
    const address = typeof arg === "string" ? arg : arg.address;
    routeNav(parseAddress(address));
  };

  // Sidebar only knows: "home" | "inbox" | "outbox" | "kg" | "settings".
  const sidebarActive: "home" | "inbox" | "outbox" | "kg" | "settings" =
    active === "chat" ? "inbox" : active === "bridge" ? "settings" : (active as any);

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column" }}>
      <TopBar
        onNavigate={handleNavigate}
        onOpenSidebar={() => setSidebarOpen(true)}
        onAskAion={() => alert("AION panel will open here.")}
        onToggleWaves={() => setShowWaves((v) => !v)}
        wavesCount={wavesCount}
        radioStatus={radioStatus}
        session={session}
        onLogout={logout}
      />

      <Sidebar
        open={sidebarOpen}
        active={sidebarActive}
        onSelect={(id) => setActive((id as unknown) as Exclude<ActiveTab, "chat" | "bridge">)}
        onClose={() => setSidebarOpen(false)}
      />

      <main style={{ flex: 1, padding: 16, background: "#f8fafc", overflow: "auto" }}>
        {active === "home" && (
          <>
            <h1>Glyph Net</h1>
            <p>
              Send your first wave <code>www.tessaris.tp</code>.
            </p>
          </>
        )}

        {active === "chat" ? (
          <div style={{ height: "calc(100vh - 96px)" }}>
            <ChatThread defaultTopic={chatTopicFromHash || "ucs://local/ucs_hub"} defaultGraph={chatKGFromHash} />
          </div>
        ) : active === "bridge" ? (
          <div style={{ height: "calc(100vh - 96px)" }}>
            <BridgePanel />
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

      {showToast && (
        <div
          style={{
            position: "fixed",
            left: "50%",
            transform: "translateX(-50%)",
            bottom: 24,
            padding: "10px 14px",
            borderRadius: 10,
            background: "#e6f7ed",
            color: "#065f46",
            fontWeight: 700,
            border: "1px solid #a7f3d0",
            boxShadow: "0 10px 30px rgba(0,0,0,.12)",
            zIndex: 60,
          }}
        >
          ✅ Radio healthy
        </div>
      )}
    </div>
  );
}