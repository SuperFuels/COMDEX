// frontend/components/Sidebar.tsx
'use client'
import Link from 'next/link'
import { DarkModeToggle } from './DarkModeToggle'

interface SidebarProps {
  isOpen: boolean
  onClose: () => void
}

export default function Sidebar({ isOpen, onClose }: SidebarProps) {
  return (
    <div
      className={`fixed inset-y-0 left-0 z-40 w-64 bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700 transform ${
        isOpen ? 'translate-x-0' : '-translate-x-full'
      } transition-transform duration-300 ease-in-out`}
    >
      <div className="flex flex-col h-full">
        {/* ─── Header of Sidebar ──────────────────────────────────── */}
        <div className="px-4 pt-4 pb-2 flex justify-between items-center border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-xl font-semibold text-text">Stickey.ai</h2>
          <button
            onClick={onClose}
            className="p-1 focus:outline-none"
            aria-label="Close sidebar"
          >
            {/* Simple “X” icon */}
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-5 w-5 text-text"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fillRule="evenodd"
                d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 
                   111.414 1.414L11.414 10l4.293 4.293a1 1 0 
                   01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 
                   01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                clipRule="evenodd"
              />
            </svg>
          </button>
        </div>

        {/* ─── Navigation Links ───────────────────────────────────── */}
        <nav className="flex-1 px-4 py-6 space-y-4 overflow-y-auto">
          <Link href="/" onClick={onClose}>
            <a className="block py-2 px-3 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-text">
              Marketplace
            </a>
          </Link>
          <Link href="/supplier/dashboard" onClick={onClose}>
            <a className="block py-2 px-3 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-text">
              Supplier Dashboard
            </a>
          </Link>
          <Link href="/buyer/dashboard" onClick={onClose}>
            <a className="block py-2 px-3 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-text">
              Buyer Dashboard
            </a>
          </Link>
          <Link href="/admin/dashboard" onClick={onClose}>
            <a className="block py-2 px-3 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-text">
              Admin Dashboard
            </a>
          </Link>
          <Link href="/register" onClick={onClose}>
            <a className="block py-2 px-3 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-text">
              Register
            </a>
          </Link>
          <Link href="/login" onClick={onClose}>
            <a className="block py-2 px-3 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-text">
              Login
            </a>
          </Link>
        </nav>

        {/* ─── Dark Mode Toggle at Bottom ─────────────────────────── */}
        <div className="px-4 pb-4 border-t border-gray-200 dark:border-gray-700">
          <DarkModeToggle />
        </div>
      </div>
    </div>
  )
}