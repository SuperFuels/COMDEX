"use client"

import { useRef, useEffect } from "react"
import Link from "next/link"
import { DarkModeToggle } from "./DarkModeToggle"
import { UserRole } from "@/hooks/useAuthRedirect"

interface SidebarProps {
  isOpen: boolean
  onClose: () => void
  role: UserRole | null
  account: string | null
  onLogout: () => void
}

type Item = { label: string; href: string; emoji?: string }
type Section = { title: string; items: Item[] }

// ✅ Master nav sections
const SECTIONS: Section[] = [
  {
    title: "AION",
    items: [
      { label: "Dashboard", href: "/aion/AIONDashboard", emoji: "🧠" },
      { label: "Codex HUD", href: "/aion/codex-hud", emoji: "📟" },
      { label: "Glyph Replay", href: "/aion/replay", emoji: "🎞️" },
      { label: "GlyphNet", href: "/aion/glyphnet", emoji: "🕸️" },
      { label: "Glyph Synthesis", href: "/aion/glyph-synthesis", emoji: "🧪" },
      { label: "Entanglement", href: "/aion/entanglement", emoji: "➿" },
      { label: "Codex Playground", href: "/aion/codex-playground", emoji: "🧩" },
      { label: "Vault UI", href: "/aion/vaultUI", emoji: "🔐" },
      { label: "QWave Field HUD", href: "/aion/qwave-field-hud", emoji: "🌊" },
      { label: "Glyph Summary HUD", href: "/aion/glyph-summary-hud", emoji: "📝" },
      { label: "GlyphNet HUD", href: "/aion/glyphnet-hud", emoji: "🖥️" },
    ],
  },
  {
    title: "Hologram",
    items: [
      { label: "Holographic Viewer", href: "/aion/holographic-viewer", emoji: "🌌" },
      { label: "Hologram HUD", href: "/aion/hologram-hud", emoji: "🪞" },
      { label: "GHX Visualizer", href: "/aion/ghx-visualizer", emoji: "🔦" },
      { label: "Quantum Field Canvas", href: "/aion/quantum-field", emoji: "🪐" },
      { label: "Quantum Field Canvas (Alt)", href: "/aion/quantum-field-canvas", emoji: "🌀" },
    ],
  },
  {
    title: "Containers",
    items: [
      { label: "Container Map (2D)", href: "/aion/ContainerMap", emoji: "🗺️" },
      { label: "Container Map (3D)", href: "/aion/container-map-3d", emoji: "🧊" },
      { label: "Atom Node 3D", href: "/aion/atom-node-3d", emoji: "⚛️" },
    ],
  },
  {
    title: "Glyph Grid",
    items: [
      { label: "Grid (3D)", href: "/aion/glyph-grid-3d", emoji: "🔳" },
      { label: "Grid (2D)", href: "/aion/glyph-grid", emoji: "🟦" },
      { label: "GlyphNet Terminal", href: "/aion/glyphnet-terminal", emoji: "💻" },
    ],
  },
  {
    title: "Runtime",
    items: [{ label: "Avatar Runtime", href: "/aion/avatar-runtime", emoji: "👤" }],
  },
  {
    title: "Research / Tools",
    items: [
      { label: "Knowledge Brain Map", href: "/aion/KnowledgeBrainMap", emoji: "🧭" },
      { label: "Lean Injector", href: "/aion/lean-injector", emoji: "📐" },
      { label: "SoulLaw HUD", href: "/aion/soul-law", emoji: "⚖️" },
    ],
  },
  {
    title: "SCI Panels",
    items: [
      { label: "Sci Panel Host", href: "/sci/SciPanelHost", emoji: "🗂️" },
      { label: "SQS Panel", href: "/sci/sci_sqs_panel", emoji: "📨" },
      { label: "AtomSheet Panel", href: "/sci/sci_atomsheet_panel", emoji: "📄" },
    ],
  },
]

export default function Sidebar({
  isOpen,
  onClose,
  role,
  account,
  onLogout,
}: SidebarProps) {
  const containerRef = useRef<HTMLDivElement>(null)

  // Close on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (isOpen && containerRef.current && !containerRef.current.contains(e.target as Node)) {
        onClose()
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [isOpen, onClose])

  return (
    <>
      {/* Backdrop */}
      <div
        className={`fixed inset-0 bg-black/40 z-30 transition-opacity ${
          isOpen ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"
        }`}
        onClick={onClose}
      />

      {/* Sidebar panel */}
      <div
        ref={containerRef}
        className={`
          fixed inset-y-0 left-0 z-40 w-72 max-w-full
          bg-white dark:bg-gray-900 border-r border-gray-300 dark:border-gray-700
          transform transition-transform duration-300 ease-in-out
          ${isOpen ? "translate-x-0" : "-translate-x-full"}
        `}
      >
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="px-4 pt-4 pb-2 flex justify-between items-center border-b border-gray-300 dark:border-gray-700">
            <h2 className="text-xl font-semibold text-black dark:text-white">Stickey.ai</h2>
            <button onClick={onClose} className="p-1 focus:outline-none" aria-label="Close sidebar">
              ✕
            </button>
          </div>

          {/* Nav sections */}
          <nav className="flex-1 px-4 py-6 overflow-y-auto space-y-6">
            {/* Live Market pinned link */}
            <Link
              href="/"
              onClick={onClose}
              className="block py-2 px-3 border border-black rounded hover:bg-gray-100 dark:hover:bg-gray-800 font-medium"
            >
              🟢 Live Market
            </Link>

            {SECTIONS.map((sec) => (
              <div key={sec.title}>
                <div className="px-2 text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-2">
                  {sec.title}
                </div>
                <div className="flex flex-col space-y-1">
                  {sec.items.map((it) => (
                    <Link
                      key={it.href}
                      href={it.href}
                      onClick={onClose}
                      className="flex items-center gap-2 py-2 px-3 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-sm"
                    >
                      <span className="w-5 text-center">{it.emoji ?? "•"}</span>
                      <span>{it.label}</span>
                    </Link>
                  ))}
                </div>
              </div>
            ))}

            {/* Role/Account-specific */}
            {role && (
              <Link
                href={
                  role === "admin"
                    ? "/admin/dashboard"
                    : role === "supplier"
                    ? "/supplier/dashboard"
                    : role === "buyer"
                    ? "/buyer/dashboard"
                    : "/"
                }
                onClick={onClose}
                className="block py-2 px-3 border border-black rounded hover:bg-gray-100 dark:hover:bg-gray-800"
              >
                Dashboard
              </Link>
            )}

            {role === "supplier" && (
              <Link
                href="/supplier/inventory"
                onClick={onClose}
                className="block py-2 px-3 border border-black rounded hover:bg-gray-100 dark:hover:bg-gray-800"
              >
                Manage Inventory
              </Link>
            )}

            {!account && !role && (
              <>
                <Link
                  href="/login"
                  onClick={onClose}
                  className="block py-2 px-3 border border-black rounded hover:bg-gray-100 dark:hover:bg-gray-800"
                >
                  Login
                </Link>
                <Link
                  href="/register"
                  onClick={onClose}
                  className="block py-2 px-3 border border-black rounded hover:bg-gray-100 dark:hover:bg-gray-800"
                >
                  Register
                </Link>
              </>
            )}

            {account && role && (
              <>
                <Link
                  href="/profile"
                  onClick={onClose}
                  className="block py-2 px-3 border border-black rounded hover:bg-gray-100 dark:hover:bg-gray-800"
                >
                  Profile
                </Link>
                <Link
                  href="/settings"
                  onClick={onClose}
                  className="block py-2 px-3 border border-black rounded hover:bg-gray-100 dark:hover:bg-gray-800"
                >
                  Settings
                </Link>
                <button
                  onClick={() => {
                    onLogout()
                    onClose()
                  }}
                  className="w-full text-left py-2 px-3 border border-black rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-sm"
                >
                  Logout
                </button>
              </>
            )}
          </nav>

          {/* Footer */}
          <div className="px-4 pb-4 border-t border-gray-300 dark:border-gray-700">
            <DarkModeToggle />
          </div>
        </div>
      </div>
    </>
  )
}