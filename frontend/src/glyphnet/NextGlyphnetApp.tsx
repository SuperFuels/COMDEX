"use client";

import React, { useCallback, useMemo, useState } from "react";
import { HashRouter, Routes, Route, Navigate, useNavigate } from "react-router-dom";

import DevTools from "./routes/DevTools";
import GlyphNetNavbar from "./components/GlyphNetNavbar";
import GlyphNetSidebar from "./components/GlyphNetSidebar";

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
      <GlyphNetNavbar onOpenSidebar={() => setSidebarOpen(true)} />

      <GlyphNetSidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        items={navItems}
        onGo={go}
      />

      {/* Content area (match your site spacing under sticky header) */}
      <main className="min-h-[calc(100vh-4rem)] bg-background text-text">
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