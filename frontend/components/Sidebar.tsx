// frontend/components/Sidebar.tsx
import { useState, useRef, useEffect } from 'react'
import Link from 'next/link'
import { DarkModeToggle } from './DarkModeToggle'

export default function Sidebar() {
  const [isOpen, setIsOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  // When clicking outside the sidebar, close it:
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (
        isOpen &&
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen])

  return (
    <>
      {/* ── Hamburger button (always visible in top‐left) ────────────────── */}
      <button
        onClick={() => setIsOpen((o) => !o)}
        className="fixed top-4 left-4 z-50 p-2 rounded-md bg-white border border-gray-200 dark:bg-gray-900 dark:border-gray-700 shadow-sm focus:outline-none"
        aria-label={isOpen ? 'Close sidebar' : 'Open sidebar'}
      >
        {/* Simple 3‐line “hamburger” icon */}
        {isOpen ? (
          /* X icon when open */
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-6 w-6 text-text-primary dark:text-text-secondary"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        ) : (
          /* Hamburger icon when closed */
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-6 w-6 text-text-primary dark:text-text-secondary"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 6h16M4 12h16M4 18h16"
            />
          </svg>
        )}
      </button>

      {/* ── Sliding Sidebar itself ──────────────────────────────────────── */}
      <div
        ref={containerRef}
        className={`
          fixed inset-y-0 left-0 z-40 w-64 max-w-full
          bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700
          transform transition-transform duration-300 ease-in-out
          ${isOpen ? 'translate-x-0' : '-translate-x-full'}
        `}
      >
        <div className="flex flex-col h-full">
          <div className="px-4 pt-4 pb-2 flex justify-between items-center border-b border-gray-200 dark:border-gray-700">
            <h2 className="text-xl font-semibold text-text-primary dark:text-text-secondary">
              Stickey.ai
            </h2>
            <button
              onClick={() => setIsOpen(false)}
              className="p-1 focus:outline-none"
              aria-label="Close sidebar"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-5 w-5 text-text-primary dark:text-text-secondary"
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

          <nav className="flex-1 px-4 py-6 space-y-4 overflow-y-auto">
            <Link href="/">
              <a
                onClick={() => setIsOpen(false)}
                className="block py-2 px-3 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-text-primary dark:text-text-secondary"
              >
                Marketplace
              </a>
            </Link>
            <Link href="/supplier/dashboard">
              <a
                onClick={() => setIsOpen(false)}
                className="block py-2 px-3 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-text-primary dark:text-text-secondary"
              >
                Supplier Dashboard
              </a>
            </Link>
            <Link href="/buyer/dashboard">
              <a
                onClick={() => setIsOpen(false)}
                className="block py-2 px-3 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-text-primary dark:text-text-secondary"
              >
                Buyer Dashboard
              </a>
            </Link>
            <Link href="/admin/dashboard">
              <a
                onClick={() => setIsOpen(false)}
                className="block py-2 px-3 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-text-primary dark:text-text-secondary"
              >
                Admin Dashboard
              </a>
            </Link>
            <Link href="/products/new">
              <a
                onClick={() => setIsOpen(false)}
                className="block py-2 px-3 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-text-primary dark:text-text-secondary"
              >
                + Sell Product
              </a>
            </Link>
            <Link href="/register">
              <a
                onClick={() => setIsOpen(false)}
                className="block py-2 px-3 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-text-primary dark:text-text-secondary"
              >
                Register
              </a>
            </Link>
            <Link href="/login">
              <a
                onClick={() => setIsOpen(false)}
                className="block py-2 px-3 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-text-primary dark:text-text-secondary"
              >
                Login
              </a>
            </Link>
          </nav>

          <div className="px-4 pb-4 border-t border-gray-200 dark:border-gray-700">
            <DarkModeToggle />
          </div>
        </div>
      </div>
    </>
  )
}