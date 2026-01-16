"use client";

import React, { useCallback, useMemo, useState } from "react";
import { HashRouter, Routes, Route, Navigate, useNavigate } from "react-router-dom";

import DevTools from "./routes/DevTools";
import ChatThread from "./routes/ChatThread";

import GlyphNetNavbar from "./components/GlyphNetNavbar";
import GlyphNetSidebar from "./components/GlyphNetSidebar";

import QfcHudPage from "./components/QfcHudPage";
import QfcBioPage from "./components/QfcBioPage";
import LedgerInspector from "./components/LedgerInspector";

// Optional (uncomment if you want these routes now)
// import WalletPanel from "./components/WalletPanel";
// import WaveOutbox from "./components/WaveOutbox";
// import KGDock from "./components/KGDock";

function Shell() {
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const go = useCallback(
    (path: string) => {
      navigate(path);
      setSidebarOpen(false);
    },
    [navigate],
  );

  const navItems = useMemo(
    () => [
      { label: "DevTools", path: "/devtools", emoji: "🛠️" },
      { label: "Ledger", path: "/ledger", emoji: "📒" },
      { label: "QFC HUD", path: "/qfc-hud", emoji: "🧿" },
      { label: "QFC Bio", path: "/qfc-bio", emoji: "🧬" },
      { label: "Chat", path: "/chat", emoji: "💬" },

      // Optional:
      // { label: "Wallet", path: "/wallet", emoji: "💰" },
      // { label: "Outbox", path: "/outbox", emoji: "📤" },
      // { label: "KG", path: "/kg", emoji: "🧠" },
    ],
    [],
  );

  return (
    <>
      {/* Sidebar: left rail is always visible; slide-out panel is controlled by sidebarOpen */}
      <GlyphNetSidebar
        isOpen={sidebarOpen}
        onOpen={() => setSidebarOpen(true)}
        onClose={() => setSidebarOpen(false)}
        items={navItems}
        onGo={go}
      />

      {/* Everything to the right of the left rail */}
      <div className="pl-14">
        {/* Sticky header (already has height h-16 = 4rem) */}
        <GlyphNetNavbar onOpenSidebar={() => setSidebarOpen(true)} />

        {/* Scroll container under the sticky navbar */}
        <main
          className={[
            "h-[calc(100vh-4rem)] overflow-y-auto bg-background text-text",
            // when panel is open, add extra left padding so content doesn't sit under it
            sidebarOpen ? "md:pl-80" : "",
          ].join(" ")}
        >
          <Routes>
            <Route path="/" element={<Navigate to="/devtools" replace />} />

            <Route path="/devtools" element={<DevTools />} />
            <Route path="/ledger" element={<LedgerInspector />} />

            <Route path="/qfc-hud" element={<QfcHudPage />} />
            <Route path="/qfc-bio" element={<QfcBioPage />} />

            <Route path="/chat" element={<ChatThread />} />

            {/* Optional:
            <Route path="/wallet" element={<WalletPanel />} />
            <Route path="/outbox" element={<WaveOutbox />} />
            <Route path="/kg" element={<KGDock />} />
            */}

            <Route path="/dev-tools" element={<Navigate to="/devtools" replace />} />
            <Route path="*" element={<Navigate to="/devtools" replace />} />
          </Routes>
        </main>
      </div>
    </>
  );
}

export default function NextGlyphnetApp() {
  // ✅ exactly ONE router in the entire GlyphNet tree
  return (
    <HashRouter>
      <Shell />
    </HashRouter>
  );
}