// frontend/components/Sidebar.tsx
"use client"

import { useState, useRef, useEffect } from 'react'
import Link from 'next/link'
import { DarkModeToggle } from './DarkModeToggle'
import { UserRole } from '@/hooks/useAuthRedirect'

interface SidebarProps {
  isOpen: boolean
  onClose: () => void
  role: UserRole | null
  account: string | null
  onLogout: () => void
}

export default function Sidebar({
  isOpen,
  onClose,
  role,
  account,
  onLogout,
}: SidebarProps) {
  const containerRef = useRef<HTMLDivElement>(null)

  // Close when clicking outside
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (
        isOpen &&
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        onClose()
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [isOpen, onClose])

  return (
    <>
      {/* ── Sliding Sidebar ──────────────────────────────────────────────────── */}
      <div
        ref={containerRef}
        className={`
          fixed inset-y-0 left-0 z-40 w-64 max-w-full
          bg-white dark:bg-gray-900 border-r border-black
          transform transition-transform duration-300 ease-in-out
          ${isOpen ? 'translate-x-0' : '-translate-x-full'}
        `}
      >
        <div className="flex flex-col h-full">
          <div className="px-4 pt-4 pb-2 flex justify-between items-center border-b border-black">
            <h2 className="text-xl font-semibold text-black dark:text-text-secondary">
              Stickey.ai
            </h2>
            <button
              onClick={onClose}
              className="p-1 focus:outline-none"
              aria-label="Close sidebar"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-5 w-5 text-black dark:text-text-secondary"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fillRule="evenodd"
                  d="M4.293 4.293a1 1 0 011.414 0L10 
                     8.586l4.293-4.293a1 1 0 
                     111.414 1.414L11.414 10l4.293 
                     4.293a1 1 0 01-1.414 
                     1.414L10 11.414l-4.293 
                     4.293a1 1 0 
                     01-1.414-1.414L8.586 
                     10 4.293 5.707a1 1 0 
                     010-1.414z"
                  clipRule="evenodd"
                />
              </svg>
            </button>
          </div>

          <nav className="flex-1 px-4 py-6 space-y-2 overflow-y-auto">
            {/* Live Market (always show) */}
            <Link
              href="/"
              onClick={onClose}
              className="block py-2 px-3 border border-black rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-black dark:text-text-secondary text-left"
            >
              Live Market
            </Link>

            {/* If user is logged in (anything in `role`), show Dashboard link */}
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
                onClick={onClose}
                className="block py-2 px-3 border border-black rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-black dark:text-text-secondary text-left"
              >
                Dashboard
              </Link>
            )}

            {/* If user is a supplier, show a “Manage Inventory” link */}
            {role === 'supplier' && (
              <Link
                href="/supplier/inventory"
                onClick={onClose}
                className="block py-2 px-3 border border-black rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-black dark:text-text-secondary text-left"
              >
                Manage Inventory
              </Link>
            )}

            {/* If not logged in, show Login / Register */}
            {!account && !role && (
              <>
                <Link
                  href="/login"
                  onClick={onClose}
                  className="block py-2 px-3 border border-black rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-black dark:text-text-secondary text-left"
                >
                  Login
                </Link>
                <Link
                  href="/register"
                  onClick={onClose}
                  className="block py-2 px-3 border border-black rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-black dark:text-text-secondary text-left"
                >
                  Register
                </Link>
              </>
            )}

            {/* If logged in, show Profile / Settings / Logout */}
            {account && role && (
              <>
                <Link
                  href="/profile"
                  onClick={onClose}
                  className="block py-2 px-3 border border-black rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-black dark:text-text-secondary text-left"
                >
                  Profile
                </Link>
                <Link
                  href="/settings"
                  onClick={onClose}
                  className="block py-2 px-3 border border-black rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-black dark:text-text-secondary text-left"
                >
                  Settings
                </Link>
                <button
                  onClick={() => {
                    onLogout()
                    onClose()
                  }}
                  className="w-full text-left py-2 px-3 border border-black rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-black dark:text-text-secondary text-sm"
                >
                  Logout
                </button>
              </>
            )}
          </nav>

          <div className="px-4 pb-4 border-t border-black">
            <DarkModeToggle />
          </div>
        </div>
      </div>
    </>
  )
}