// src/App.tsx
import { useEffect, useRef, useState } from "react";
import TopBar, { RadioStatus } from "./components/TopBar";
import { SidebarRail } from "./components/SidebarRail";
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
import DevTools from "./routes/DevTools";
import QfcHudPage from "./components/QfcHudPage";
import QfcBioPage from "./components/QfcBioPage";
import WalletPanel from "./components/WalletPanel";
import AdminDashboard from "./routes/AdminDashboard";
import SettingsPanel from "./components/SettingsPanel";

// 🔧 DEV-ONLY PANELS (Photon Pay + Wave send)
import PhotonPayPosPanel from "./components/PhotonPayPosPanel";
import PhotonPayBuyerPanel from "./components/PhotonPayBuyerPanel";
import WaveSendPanel from "./components/WaveSendPanel";

type Mode = "wormhole" | "http";
type NavArg = string | { mode: Mode; address: string };

type ActiveTab =
  | "home"
  | "inbox"
  | "outbox"
  | "kg"
  | "settings"
  | "chat"
  | "bridge"
  | "devtools"
  | "qfc-hud"
  | "qfc-bio"
  | "wallet"
  | "admin"
  | "dev-photon-pos"
  | "dev-photon-buyer"
  | "dev-wave-send";

type Session = { slug: string; wa: string } | null;

// ⚠️ DEV-ONLY FLAG (easy to rip out later)
const DEV_ROUTES_ENABLED =
  import.meta.env.DEV || import.meta.env.VITE_SHOW_DEV_ROUTES === "1";

export default function App() {
  const [showWaves, setShowWaves] = useState(false);
  const [active, setActive] = useState<ActiveTab>("home");
  const [wavesCount, setWavesCount] = useState(1);

  const [inboxTopicFromHash, setInboxTopicFromHash] = useState<string>("");
  const [chatTopicFromHash, setChatTopicFromHash] = useState<string>("");
  const [chatKGFromHash, setChatKGFromHash] = useState<
    "personal" | "work" | undefined
  >(undefined);

  // --- session (inline, no extra hook) ---
  const [session, setSession] = useState<Session>(null);
  const [sessionLoading, setSessionLoading] = useState<boolean>(true);

  const navAdmin = () => {
    window.location.hash = "#/admin";
    setActive("admin");
  };

  const refreshSession = () => {
    setSessionLoading(true);
    fetch("/api/session/me")
      .then((r) => (r.ok ? r.json() : null))
      .then((j) => {
        const s: Session = j?.session
          ? { slug: j.session.slug, wa: j.session.wa }
          : null;
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
    localStorage.removeItem("gnet:ownerWa");
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
      localStorage.setItem("gnet:ownerWa", session.wa); // canonical owner

      if (!location.hash || location.hash === "#/" || location.hash === "#") {
        window.location.hash = `#/container/${session.slug}__home`;
      }
    } else {
      localStorage.removeItem("gnet:user_slug");
      localStorage.removeItem("gnet:wa");
      localStorage.removeItem("gnet:ownerWa");
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

      // 🔧 DEV-ONLY HASH ROUTES
      if (DEV_ROUTES_ENABLED) {
        if (h.startsWith("#/dev/photon-pay-pos")) {
          setActive("dev-photon-pos");
          document.title = `Photon Pay POS (dev) — Glyph Net`;
          return;
        }

        if (h.startsWith("#/dev/photon-pay-buyer")) {
          setActive("dev-photon-buyer");
          document.title = `Photon Pay Buyer (dev) — Glyph Net`;
          return;
        }

        if (h.startsWith("#/dev/wave-send")) {
          setActive("dev-wave-send");
          document.title = `Wave Send (dev) — Glyph Net`;
          return;
        }
      }
      // 🔧 END DEV-ONLY HASH ROUTES

      if (h.startsWith("#/admin")) {
        setActive("admin");
        document.title = `Admin — Glyph Net`;
        return;
      }

      if (h.startsWith("#/bridge")) {
        setActive("bridge");
        document.title = `RF Bridge — Glyph Net`;
        return;
      }

      if (h.startsWith("#/devtools")) {
        setActive("devtools");
        document.title = `Dev Tools — Glyph Net`;
        return;
      }

      // ✅ QFC PAGES (from DevTools tabs)
      if (h.startsWith("#/qfc-hud")) {
        setActive("qfc-hud");
        document.title = `QFC HUD — Glyph Net`;
        return;
      }

      if (h.startsWith("#/qfc-bio")) {
        setActive("qfc-bio");
        document.title = `QFC Bio — Glyph Net`;
        return;
      }

      if (h.startsWith("#/wallet")) {
        setActive("wallet");
        document.title = `Wallet — Glyph Net`;
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
    return () =>
      window.removeEventListener("glyphnet:wave", onWave as EventListener);
  }, []);

  // KG visit/dwell journaling via UMD (/public/js/kg_emit.js)
  useEffect(() => {
    const ownerWa =
      session?.wa || localStorage.getItem("gnet:ownerWa") || OWNER_WA;

    const kgEmit = (window as any).KGEmit;
    if (!kgEmit || typeof kgEmit.initVisitEmitters !== "function") return;

    const readGraph = () => {
      try {
        return readKGFromHash(window.location.hash || "#/");
      } catch {
        return "personal" as const;
      }
    };
    const readTopic = () => {
      try {
        return (
          readTopicFromHash(window.location.hash || "#/") ||
          "ucs://local/ucs_hub"
        );
      } catch {
        return "ucs://local/ucs_hub";
      }
    };

    const stop = kgEmit.initVisitEmitters({
      apiBase: KG_API_BASE,
      ownerWa,

      // legacy snapshot (for older servers)
      kg: readGraph(),
      topicWa: readTopic(),
      getUri: () => window.location.href,
      getTitle: () => document.title,

      // live readers
      getGraph: readGraph,
      getTopic: readTopic,
      getPath: () => window.location.hash || "#/",
    });

    return () => {
      if (typeof stop === "function") stop();
    };
  }, [session?.wa]);

  // Accept both a string or an object from TopBar
  const handleNavigate = (arg: NavArg) => {
    const address = typeof arg === "string" ? arg : arg.address;
    routeNav(parseAddress(address));
  };

  // SidebarRail highlights based on current active tab
  const sidebarActive:
    | "home"
    | "inbox"
    | "outbox"
    | "kg"
    | "settings"
    | "devtools"
  | "qfc-hud"
  | "qfc-bio"
    | "chat"
    | "wallet"
    | "admin"
    | "dev-photon-pos"
    | "dev-photon-buyer"
    | "dev-wave-send" = active as any;

  // SidebarRail click handlers – keep existing routes/hash patterns
  const navHome = () => {
    if (session?.slug) {
      window.location.hash = `#/container/${session.slug}__home`;
    } else {
      window.location.hash = "#/";
    }
    setActive("home");
  };
  const navChat = () => {
    window.location.hash = "#/chat";
    setActive("chat");
  };
  const navInbox = () => {
    window.location.hash = "#/inbox";
    setActive("inbox");
  };
  const navOutbox = () => {
    window.location.hash = "#/outbox";
    setActive("outbox");
  };
  const navDevTools = () => {
    window.location.hash = "#/devtools";
    setActive("devtools");
  };
  const navWallet = () => {
    window.location.hash = "#/wallet";
    setActive("wallet");
  };

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column" }}>
      <TopBar
        onNavigate={handleNavigate}
        onOpenSidebar={() => {
          /* sidebar rail is always visible now */
        }}
        onAskAion={() => alert("AION panel will open here.")}
        onToggleWaves={() => setShowWaves((v) => !v)}
        wavesCount={wavesCount}
        radioStatus={radioStatus}
        session={session}
        onLogout={logout}
      />

      {/* main layout: slim sidebar rail + content */}
      <div style={{ flex: 1, display: "flex", minHeight: 0 }}>
        <SidebarRail
          activeId={sidebarActive}
          items={[
            { id: "home", icon: "🏠", label: "Home", onClick: navHome },
            { id: "chat", icon: "💬", label: "Chat", onClick: navChat },
            { id: "inbox", icon: "📥", label: "Inbox", onClick: navInbox },
            { id: "outbox", icon: "📤", label: "Outbox", onClick: navOutbox },
            {
              id: "wallet",
              icon: "🏦",
              label: "Wallet",
              onClick: navWallet,
            },
            {
              id: "admin" as const,
              icon: "🧰",
              label: "Admin",
              onClick: navAdmin,
            },
            {
              id: "kg",
              icon: "🧠",
              label: "KG Dock",
              onClick: () => setActive("kg"),
            },
            {
              id: "settings",
              icon: "⚙️",
              label: "Settings",
              onClick: () => setActive("settings"),
            },
            {
              id: "devtools",
              icon: "🛠️",
              label: "Dev Tools",
              onClick: navDevTools,
            },

            // 🔧 dev-only quick links under Dev Tools
            ...(DEV_ROUTES_ENABLED
              ? [
                  {
                    id: "dev-photon-pos" as const,
                    icon: "💳",
                    label: "Photon Pay POS (dev)",
                    onClick: () => {
                      window.location.hash = "#/dev/photon-pay-pos";
                      setActive("dev-photon-pos");
                    },
                  },
                  {
                    id: "dev-photon-buyer" as const,
                    icon: "🙋‍♀️",
                    label: "Photon Pay Buyer (dev)",
                    onClick: () => {
                      window.location.hash = "#/dev/photon-pay-buyer";
                      setActive("dev-photon-buyer");
                    },
                  },
                  {
                    id: "dev-wave-send" as const,
                    icon: "📡",
                    label: "Wave Send (dev)",
                    onClick: () => {
                      window.location.hash = "#/dev/wave-send";
                      setActive("dev-wave-send");
                    },
                  },
                ]
              : []),
          ]}
        />

        <main
          style={{
            flex: 1,
            padding: 16,
            background: "#f8fafc",
            overflow: "auto",
          }}
        >
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
              <ChatThread
                defaultTopic={chatTopicFromHash || "ucs://local/ucs_hub"}
                defaultGraph={chatKGFromHash}
              />
            </div>
          ) : active === "bridge" ? (
            <div style={{ height: "calc(100vh - 96px)" }}>
              <BridgePanel />
            </div>
          ) : active === "inbox" ? (
            <WaveInbox
              defaultTopic={inboxTopicFromHash || "ucs://local/ucs_hub"}
            />
          ) : active === "kg" ? (
            <KGDock />
          ) : active === "outbox" ? (
            <WaveOutbox />
          ) : active === "wallet" ? (
            <WalletPanel />
          ) : active === "admin" ? (
            <AdminDashboard />
          ) : active === "settings" ? (
            <SettingsPanel /> 
          ) : active === "devtools" ? (
            <DevTools />
          ) : active === "qfc-hud" ? (
            <QfcHudPage />
          ) : active === "qfc-bio" ? (
            <QfcBioPage />
          ) : active === "dev-photon-pos" ? (
            <PhotonPayPosPanel />
          ) : active === "dev-photon-buyer" ? (
            <PhotonPayBuyerPanel />
          ) : active === "dev-wave-send" ? (
            <WaveSendPanel />
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
        </main>
      </div>

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