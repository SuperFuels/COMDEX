// frontend/components/Sidebar.tsx
import Link from 'next/link'
import { DarkModeToggle } from './DarkModeToggle'
import { useState } from 'react'

export default function Sidebar() {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <>
      {/* ── G.svg Toggle Button ───────────────────────────────────────────────── */}
      <button
        onClick={() => setIsOpen(true)}
        aria-label="Open sidebar"
        className="
          fixed top-4 left-4 z-50 
          p-2 
          bg-transparent border border-black 
          rounded
          hover:bg-gray-100 dark:hover:bg-gray-800
          transition-colors
        "
      >
        <img src="/G.svg" alt="≡" className="h-6 w-6" />
      </button>

      {/* ── Sidebar Overlay (slides in/out) ────────────────────────────────────── */}
      <div
        className={`
          fixed inset-y-0 left-0 z-40 w-64 
          bg-white dark:bg-gray-900 
          border-r border-gray-200 dark:border-gray-700 
          transform ${
            isOpen ? 'translate-x-0' : '-translate-x-full'
          } 
          transition-transform duration-300 ease-in-out
        `}
      >
        <div className="flex flex-col h-full">
          {/* ── Sidebar Header ─────────────────────────────────────────── */}
          <div className="flex items-center justify-between px-4 pt-4 pb-2 border-b border-gray-200 dark:border-gray-700">
            <h2 className="text-xl font-semibold text-text">Stickey.ai</h2>
            <button
              onClick={() => setIsOpen(false)}
              aria-label="Close sidebar"
              className="
                p-1 focus:outline-none
                bg-transparent border border-black rounded
                hover:bg-gray-100 dark:hover:bg-gray-800
                transition-colors
              "
            >
              {/* We reuse the same G.svg but rotate it 90° to look like an “×” */}
              <img
                src="/G.svg"
                alt="×"
                className="h-5 w-5 transform rotate-90 text-text"
              />
            </button>
          </div>

          {/* ── Navigation Links ───────────────────────────────────────── */}
          <nav className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
            <Link href="/" onClick={() => setIsOpen(false)}>
              <a className="
                block py-2 px-3 rounded 
                text-text 
                hover:bg-gray-100 dark:hover:bg-gray-800 
                transition-colors
              ">
                Marketplace
              </a>
            </Link>

            <Link href="/supplier/dashboard" onClick={() => setIsOpen(false)}>
              <a className="
                block py-2 px-3 rounded 
                text-text 
                hover:bg-gray-100 dark:hover:bg-gray-800 
                transition-colors
              ">
                Supplier Dashboard
              </a>
            </Link>

            <Link href="/buyer/dashboard" onClick={() => setIsOpen(false)}>
              <a className="
                block py-2 px-3 rounded 
                text-text 
                hover:bg-gray-100 dark:hover:bg-gray-800 
                transition-colors
              ">
                Buyer Dashboard
              </a>
            </Link>

            <Link href="/admin/dashboard" onClick={() => setIsOpen(false)}>
              <a className="
                block py-2 px-3 rounded 
                text-text 
                hover:bg-gray-100 dark:hover:bg-gray-800 
                transition-colors
              ">
                Admin Dashboard
              </a>
            </Link>

            <Link href="/register" onClick={() => setIsOpen(false)}>
              <a className="
                block py-2 px-3 rounded 
                text-text 
                hover:bg-gray-100 dark:hover:bg-gray-800 
                transition-colors
              ">
                Register
              </a>
            </Link>

            <Link href="/login" onClick={() => setIsOpen(false)}>
              <a className="
                block py-2 px-3 rounded 
                text-text 
                hover:bg-gray-100 dark:hover:bg-gray-800 
                transition-colors
              ">
                Login
              </a>
            </Link>
          </nav>

          {/* ── Dark/Light Toggle in Footer ───────────────────────────────── ── */}
          <div className="px-4 pb-4 border-t border-gray-200 dark:border-gray-700">
            <DarkModeToggle />
          </div>
        </div>
      </div>
    </>
  )
}