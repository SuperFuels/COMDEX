// frontend/components/Sidebar.tsx
'use client'

import { useRef, useEffect } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { DarkModeToggle } from './DarkModeToggle'
import { UserRole } from '@/hooks/useAuthRedirect'

interface SidebarProps {
  isOpen: boolean
  onClose: () => void
  role: UserRole | null
  account: string | null
  onLogout: () => void
}

type Item = { label: string; href: string; emoji?: string }
type Section = { title: string; items: Item[] }

// Keep everything you had (plus a Products link that matched the old “Live” button)
const SECTIONS: Section[] = [
  {
    title: 'AION',
    items: [
      { label: 'Dashboard', href: '/aion/AIONDashboard', emoji: '🧠' },
      { label: 'Codex HUD', href: '/aion/codex-hud', emoji: '📟' },
      { label: 'Glyph Replay', href: '/aion/replay', emoji: '🎞️' },
      { label: 'GlyphNet', href: '/aion/glyphnet', emoji: '🕸️' },
      { label: 'Glyph Synthesis', href: '/aion/glyph-synthesis', emoji: '🧪' },
      { label: 'Entanglement', href: '/aion/entanglement', emoji: '➿' },
      { label: 'Codex Playground', href: '/aion/codex-playground', emoji: '🧩' },
      { label: 'Vault UI', href: '/aion/vaultUI', emoji: '🔐' },
      { label: 'QWave Field HUD', href: '/aion/qwave-field-hud', emoji: '🌊' },
      { label: 'Glyph Summary HUD', href: '/aion/glyph-summary-hud', emoji: '📝' },
      { label: 'GlyphNet HUD', href: '/aion/glyphnet-hud', emoji: '🖥️' },
    ],
  },
  {
    title: 'Hologram',
    items: [
      { label: 'Holographic Viewer', href: '/aion/holographic-viewer', emoji: '🌌' },
      { label: 'Hologram HUD', href: '/aion/hologram-hud', emoji: '🪞' },
      { label: 'GHX Visualizer', href: '/aion/ghx-visualizer', emoji: '🔦' },
      { label: 'Quantum Field Canvas', href: '/aion/quantum-field', emoji: '🪐' },
      { label: 'Quantum Field Canvas (Alt)', href: '/aion/quantum-field-canvas', emoji: '🌀' },
    ],
  },
  {
    title: 'Containers',
    items: [
      { label: 'Container Map (2D)', href: '/aion/ContainerMap', emoji: '🗺️' },
      { label: 'Container Map (3D)', href: '/aion/container-map-3d', emoji: '🧊' },
      { label: 'Atom Node 3D', href: '/aion/atom-node-3d', emoji: '⚛️' },
    ],
  },
  {
    title: 'Glyph Grid',
    items: [
      { label: 'Grid (3D)', href: '/aion/glyph-grid-3d', emoji: '🔳' },
      { label: 'Grid (2D)', href: '/aion/glyph-grid', emoji: '🟦' },
      { label: 'GlyphNet Terminal', href: '/aion/glyphnet-terminal', emoji: '💻' },
    ],
  },
  {
    title: 'Runtime',
    items: [{ label: 'Avatar Runtime', href: '/aion/avatar-runtime', emoji: '👤' }],
  },
  {
    title: 'Research / Tools',
    items: [
      { label: 'Knowledge Brain Map', href: '/aion/KnowledgeBrainMap', emoji: '🧭' },
      { label: 'Lean Injector', href: '/aion/lean-injector', emoji: '📐' },
      { label: 'SoulLaw HUD', href: '/aion/soul-law', emoji: '⚖️' },
    ],
  },
  {
    title: 'SCI Panels',
    items: [
      { label: 'Sci Panel Host', href: '/sci/SciPanelHost', emoji: '🗂️' },
      { label: 'SQS Panel', href: '/sci/sci_sqs_panel', emoji: '📨' },
      { label: 'AtomSheet Panel', href: '/sci/sci_atomsheet_panel', emoji: '📄' },
    ],
  },
  {
  title: 'Tessaris Dashboards',
  items: [
    {
      label: 'Symatics Dashboard',
      href: 'https://glowing-space-train-r467j79vv5xg2wj4p-5173.app.github.dev',
      emoji: '💡',
    },
    {
      label: 'Harmonic Coherence',
      href: 'https://glowing-space-train-r467j79vv5xg2wj4p-5174.app.github.dev',
      emoji: '🎛️',
    },
    {
      label: 'Resonant Field Visualizer',
      href: 'https://glowing-space-train-r467j79vv5xg2wj4p-5175.app.github.dev',
      emoji: '🌀',
    },
    {
      label: 'Symbolic Export Layer',
      href: 'https://glowing-space-train-r467j79vv5xg2wj4p-5176.app.github.dev',
      emoji: '🪶',
    },
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
  const pathname = usePathname()

  // Close when clicking outside
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (isOpen && containerRef.current && !containerRef.current.contains(e.target as Node)) {
        onClose()
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [isOpen, onClose])

  // Close on route change (so it doesn’t stay open)
  useEffect(() => {
    if (isOpen) onClose()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname])

  return (
    <>
      {/* Backdrop */}
      <div
        className={`fixed inset-0 bg-black/40 z-30 transition-opacity ${
          isOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
        }`}
        onClick={onClose}
      />

      {/* Panel */}
      <aside
        ref={containerRef}
        className={`fixed inset-y-0 left-0 z-40 w-72 max-w-full
          bg-white dark:bg-gray-900 border-r border-gray-300 dark:border-gray-700
          transform transition-transform duration-300 ease-in-out
          ${isOpen ? 'translate-x-0' : '-translate-x-full'}`}
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
            {/* Pinned links (keeps your old top-bar actions) */}
            <div className="flex flex-col gap-2">
              <Link
                href="/"
                className="block py-2 px-3 border border-black rounded hover:bg-gray-100 dark:hover:bg-gray-800 font-medium"
              >
                🟢 Home / Live Market
              </Link>
              <Link
                href="/products"
                className="block py-2 px-3 border border-black rounded hover:bg-gray-100 dark:hover:bg-gray-800 font-medium"
              >
                🛒 Products
              </Link>
              <Link
                href="/swap"
                className="block py-2 px-3 border border-black rounded hover:bg-gray-100 dark:hover:bg-gray-800 font-medium"
              >
                🔁 Swap
              </Link>
            </div>

            {SECTIONS.map((sec) => (
              <section key={sec.title}>
                <div className="mb-2 px-2 text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
                  {sec.title}
                </div>
                <div className="flex flex-col">
                  {sec.items.map((it) => (
                    <Link
                      key={it.href}
                      href={it.href}
                      className="flex items-center gap-2 py-2 px-3 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-sm"
                    >
                      <span className="w-5 text-center">{it.emoji ?? '•'}</span>
                      <span>{it.label}</span>
                    </Link>
                  ))}
                </div>
              </section>
            ))}

            {/* Role / account specific */}
            {role && (
              <Link
                href={
                  role === 'admin'
                    ? '/admin/dashboard'
                    : role === 'supplier'
                    ? '/supplier/dashboard'
                    : role === 'buyer'
                    ? '/buyer/dashboard'
                    : '/'
                }
                className="block py-2 px-3 border border-black rounded hover:bg-gray-100 dark:hover:bg-gray-800"
              >
                Dashboard
              </Link>
            )}

            {role === 'supplier' && (
              <Link
                href="/supplier/inventory"
                className="block py-2 px-3 border border-black rounded hover:bg-gray-100 dark:hover:bg-gray-800"
              >
                Manage Inventory
              </Link>
            )}

            {!account && !role && (
              <div className="flex flex-col gap-2">
                <Link
                  href="/login"
                  className="block py-2 px-3 border border-black rounded hover:bg-gray-100 dark:hover:bg-gray-800"
                >
                  Login
                </Link>
                <Link
                  href="/register"
                  className="block py-2 px-3 border border-black rounded hover:bg-gray-100 dark:hover:bg-gray-800"
                >
                  Register
                </Link>
              </div>
            )}

            {account && role && (
              <div className="flex flex-col gap-2">
                <Link
                  href="/profile"
                  className="block py-2 px-3 border border-black rounded hover:bg-gray-100 dark:hover:bg-gray-800"
                >
                  Profile
                </Link>
                <Link
                  href="/settings"
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
              </div>
            )}
          </nav>

          {/* Footer */}
          <div className="px-4 pb-4 border-t border-gray-300 dark:border-gray-700">
            <DarkModeToggle />
          </div>
        </div>
      </aside>
    </>
  )
}