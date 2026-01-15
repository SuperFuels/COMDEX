"use client";

import React, { useCallback, useMemo, useState } from "react";
import { HashRouter, Routes, Route, Navigate, useNavigate } from "react-router-dom";

import DevTools from "./routes/DevTools";
import GlyphNetNavbar from "./components/GlyphNetNavbar";
import GlyphNetSidebar from "./components/GlyphNetSidebar";

function Shell() {
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const openSidebar = useCallback(() => setSidebarOpen(true), []);
  const closeSidebar = useCallback(() => setSidebarOpen(false), []);

  const go = useCallback(
    (path: string) => {
      navigate(path);
      setSidebarOpen(false);
    },
    [navigate],
  );

  // very small route map (add more as you wire pages)
  const navItems = useMemo(
    () => [
      { label: "DevTools", path: "/devtools", emoji: "🛠️" },
      // add more when you create routes:
      // { label: "Inbox", path: "/inbox", emoji: "📥" },
      // { label: "Outbox", path: "/outbox", emoji: "📤" },
      // { label: "Knowledge Graph", path: "/kg", emoji: "🧠" },
      // { label: "Wallet", path: "/wallet", emoji: "🏦" },
      // { label: "Settings", path: "/settings", emoji: "⚙️" },
    ],
    [],
  );

  return (
    <>
      {/* Sticky top navbar */}
      <GlyphNetNavbar onOpenSidebar={openSidebar} />

      {/* ChatGPT-style rail + slideout */}
      <GlyphNetSidebar
        isOpen={sidebarOpen}
        onOpen={openSidebar}
        onClose={closeSidebar}
        items={navItems}
        onGo={go}
      />

      {/* Content:
          - pt-16 to sit under sticky navbar (h-16)
          - pl-14 so the always-on rail doesn't overlap content
      */}
      <main className="min-h-screen bg-background text-text pt-16 pl-14">
        <Routes>
          {/* land somewhere useful */}
          <Route path="/" element={<Navigate to="/devtools" replace />} />
          <Route path="/devtools" element={<DevTools />} />

          {/* aliases */}
          <Route path="/dev-tools" element={<Navigate to="/devtools" replace />} />

          {/* fallback */}
          <Route path="*" element={<Navigate to="/devtools" replace />} />
        </Routes>
      </main>
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