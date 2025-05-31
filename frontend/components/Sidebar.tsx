// frontend/components/Sidebar.tsx
import Link from 'next/link'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/router'

export default function Sidebar() {
  const router = useRouter()
  const [isOpen, setIsOpen] = useState(false)

  // Whenever the URL changes, close the sidebar
  useEffect(() => {
    const handleRouteChange = () => setIsOpen(false)
    router.events.on('routeChangeStart', handleRouteChange)
    return () => {
      router.events.off('routeChangeStart', handleRouteChange)
    }
  }, [router.events])

  // Mirror the `sidebarOpen` state on <body> as a class
  useEffect(() => {
    const body = document.body
    if (isOpen) {
      body.classList.add('sidebar-open')
    } else {
      body.classList.remove('sidebar-open')
    }
  }, [isOpen])

  return (
    <>
      {/* Invisible toggle anchor; actual trigger lives in Navbar */}
      <button
        id="sidebarToggle" 
        onClick={() => setIsOpen(prev => !prev)}
        className="sr-only"
      >
        Toggle sidebar
      </button>

      {/* Sidebar panel */}
      <div
        className={
          `fixed inset-y-0 left-0 z-30 w-64 bg-white dark:bg-background-dark shadow transition-transform duration-300
           transform ${isOpen ? 'translate-x-0' : '-translate-x-full'}` 
        }
      >
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-text">Menu</h2>
          <button onClick={() => setIsOpen(false)} className="text-text hover:text-primary">
            ✕
          </button>
        </div>
        <nav className="mt-4 px-4 space-y-2">
          <Link href="/" className="block px-3 py-2 rounded hover:bg-gray-100 dark:hover:bg-gray-800">
            <span className="text-text">Marketplace</span>
          </Link>
          <Link href="/supplier/dashboard" className="block px-3 py-2 rounded hover:bg-gray-100 dark:hover:bg-gray-800">
            <span className="text-text">Supplier Dashboard</span>
          </Link>
          <Link href="/buyer/dashboard" className="block px-3 py-2 rounded hover:bg-gray-100 dark:hover:bg-gray-800">
            <span className="text-text">Buyer Dashboard</span>
          </Link>
          <Link href="/admin/dashboard" className="block px-3 py-2 rounded hover:bg-gray-100 dark:hover:bg-gray-800">
            <span className="text-text">Admin Dashboard</span>
          </Link>
          <Link href="/register" className="block px-3 py-2 rounded hover:bg-gray-100 dark:hover:bg-gray-800">
            <span className="text-text">Register</span>
          </Link>
          <Link href="/login" className="block px-3 py-2 rounded hover:bg-gray-100 dark:hover:bg-gray-800">
            <span className="text-text">Login</span>
          </Link>
        </nav>
      </div>

      {/* Overlay behind Sidebar (only shown when open) */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-25 z-20"
          onClick={() => setIsOpen(false)}
        />
      )}
    </>
  )
}