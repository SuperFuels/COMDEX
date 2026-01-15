"use client";

import { useEffect, useRef, useState } from "react";
import { DarkModeToggle } from "../../../components/DarkModeToggle";

// NOTE: We use <a href> instead of next/link + usePathname,
// because GlyphNet is running inside pages-router + HashRouter.
// This avoids app-router hooks and keeps navigation reliable.

type Item = { label: string; href: string; emoji?: string };
type Section = { title: string; items: Item[] };

const GLYPHNET_PREFIX = "/glyphnet";

// GlyphNet INTERNAL routes (HashRouter)
const GLYPHNET_ITEMS: Item[] = [
  { label: "DevTools", href: `${GLYPHNET_PREFIX}/#/devtools`, emoji: "🛠️" },
  // add more as you create them:
  // { label: "Home", href: `${GLYPHNET_PREFIX}/#/`, emoji: "🏠" },
];

// Your existing “main app” sections (external to glyphnet)
const SECTIONS: Section[] = [
  {
    title: "AION",
    items: [
      { label: "Dashboard", href: "/aion/AIONDashboard", emoji: "🧠" },
      { label: "Codex HUD", href: "/aion/codex-hud", emoji: "📟" },
      { label: "Glyph Replay", href: "/aion/replay", emoji: "🎞️" },
      { label: "GlyphNet (Old)", href: "/aion/glyphnet", emoji: "🕸️" },
      { label: "Glyph Synthesis", href: "/aion/glyph-synthesis", emoji: "🧪" },
      { label: "Entanglement", href: "/aion/entanglement", emoji: "➿" },
      { label: "Codex Playground", href: "/aion/codex-playground", emoji: "🧩" },
      { label: "Vault UI", href: "/aion/vaultUI", emoji: "🔐" },
      { label: "GlyphNet (New)", href: "/glyphnet", emoji: "🕸️" },
    ],
  },
  {
    title: "Hologram",
    items: [
      { label: "Holographic Viewer", href: "/aion/holographic-viewer", emoji: "🌌" },
      { label: "GHX Visualizer", href: "/aion/ghx-visualizer", emoji: "🔦" },
      { label: "Quantum Field Canvas", href: "/aion/quantum-field", emoji: "🪐" },
    ],
  },
  {
    title: "SCI IDE / PhotonLang",
    items: [
      { label: "SCI IDE", href: "/sci", emoji: "🧠" },
      { label: "Memory Scrolls", href: "/sci/SciMemoryPanel", emoji: "📜" },
      { label: "Lean Proof Export", href: "/sci/LeanExportPanel", emoji: "📐" },
    ],
  },
];

export default function Sidebar({
  isOpen,
  onClose,
}: {
  isOpen: boolean;
  onClose: () => void;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [locKey, setLocKey] = useState("");

  // Close when clicking outside
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (isOpen && containerRef.current && !containerRef.current.contains(e.target as Node)) {
        onClose();
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen, onClose]);

  // Close on navigation (hash changes etc.)
  useEffect(() => {
    const bump = () => setLocKey(`${window.location.pathname}${window.location.hash}`);
    bump();
    window.addEventListener("hashchange", bump);
    window.addEventListener("popstate", bump);
    return () => {
      window.removeEventListener("hashchange", bump);
      window.removeEventListener("popstate", bump);
    };
  }, []);

  useEffect(() => {
    if (isOpen) onClose();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [locKey]);

  const isActive = (href: string) => {
    // mark active for glyphnet hash links + normal paths
    const cur = `${window.location.pathname}${window.location.hash}`;
    if (href.includes("#/")) return cur.includes(href.replace(GLYPHNET_PREFIX, ""));
    return window.location.pathname === href;
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className={`fixed inset-0 bg-black/40 z-30 transition-opacity ${
          isOpen ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"
        }`}
        onClick={onClose}
      />

      {/* Panel */}
      <aside
        ref={containerRef}
        className={`fixed inset-y-0 left-0 z-40 w-72 max-w-full
          bg-white dark:bg-gray-900 border-r border-gray-300 dark:border-gray-700
          transform transition-transform duration-300 ease-in-out
          ${isOpen ? "translate-x-0" : "-translate-x-full"}`}
        aria-label="Primary navigation"
      >
        <div className="flex h-full flex-col">
          {/* Header */}
          <div className="flex items-center justify-between px-4 pt-4 pb-2 border-b border-gray-300 dark:border-gray-700">
            <h2 className="text-xl font-semibold">Stickey.ai</h2>
            <button
              onClick={onClose}
              className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800"
              aria-label="Close sidebar"
            >
              ✕
            </button>
          </div>

          {/* Nav */}
          <nav className="flex-1 overflow-y-auto px-4 py-6 space-y-6">
            {/* Pinned */}
            <div className="flex flex-col gap-2">
              <a
                href="/"
                className="block py-2 px-3 border border-black rounded hover:bg-gray-100 dark:hover:bg-gray-800 font-medium"
              >
                🟢 Home / Live Market
              </a>
              <a
                href="/products"
                className="block py-2 px-3 border border-black rounded hover:bg-gray-100 dark:hover:bg-gray-800 font-medium"
              >
                🛒 Products
              </a>
              <a
                href="/glyphnet"
                className="block py-2 px-3 border border-black rounded hover:bg-gray-100 dark:hover:bg-gray-800 font-medium"
              >
                🕸️ GlyphNet (New)
              </a>
            </div>

            {/* GlyphNet internal */}
            <section>
              <div className="mb-2 px-2 text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
                GlyphNet
              </div>
              <div className="flex flex-col">
                {GLYPHNET_ITEMS.map((it) => (
                  <a
                    key={it.href}
                    href={it.href}
                    className={`flex items-center gap-2 py-2 px-3 rounded text-sm ${
                      isActive(it.href)
                        ? "bg-gray-100 dark:bg-gray-800"
                        : "hover:bg-gray-100 dark:hover:bg-gray-800"
                    }`}
                  >
                    <span className="w-5 text-center">{it.emoji ?? "•"}</span>
                    <span>{it.label}</span>
                  </a>
                ))}
              </div>
            </section>

            {/* Rest of app */}
            {SECTIONS.map((sec) => (
              <section key={sec.title}>
                <div className="mb-2 px-2 text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
                  {sec.title}
                </div>
                <div className="flex flex-col">
                  {sec.items.map((it) => (
                    <a
                      key={it.href}
                      href={it.href}
                      className={`flex items-center gap-2 py-2 px-3 rounded text-sm ${
                        isActive(it.href)
                          ? "bg-gray-100 dark:bg-gray-800"
                          : "hover:bg-gray-100 dark:hover:bg-gray-800"
                      }`}
                    >
                      <span className="w-5 text-center">{it.emoji ?? "•"}</span>
                      <span>{it.label}</span>
                    </a>
                  ))}
                </div>
              </section>
            ))}
          </nav>

          {/* Footer */}
          <div className="px-4 pb-4 border-t border-gray-300 dark:border-gray-700">
            <DarkModeToggle />
          </div>
        </div>
      </aside>
    </>
  );
}