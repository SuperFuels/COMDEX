// frontend/components/Navbar.tsx
import Link from 'next/link'
import Image from 'next/image'
import { useRouter } from 'next/router'
import { useEffect, useState, useRef, useCallback } from 'react'
import api from '@/lib/api'
import { UserRole } from '@/hooks/useAuthRedirect'
import { signInWithEthereum, logout } from '@/utils/auth'
import Sidebar from './Sidebar'

export default function Navbar() {
  const router = useRouter()
  const [account, setAccount] = useState<string | null>(null)
  const [role, setRole] = useState<UserRole | null>(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const wrapperRef = useRef<HTMLDivElement>(null)

  // 1) SIWE login via wallet
  const handleConnect = useCallback(async () => {
    localStorage.removeItem('manualDisconnect')
    try {
      const { address, role: newRole } = await signInWithEthereum()
      setAccount(address)
      setRole(newRole as UserRole)
    } catch (err: any) {
      console.error('SIWE login failed', err)
      if (err.response?.status === 404) router.push('/register')
    }
  }, [router])

  // 2) Manual logout
  const handleDisconnect = useCallback(() => {
    localStorage.setItem('manualDisconnect', 'true')
    logout()
    setAccount(null)
    setRole(null)
    setSidebarOpen(false)
    router.push('/')
  }, [router])

  // 3) Hydrate JWT and/or wallet on mount
  useEffect(() => {
    // JWT login
    const token = localStorage.getItem('token')
    if (token) {
      api.defaults.headers.common.Authorization = `Bearer ${token}`
      api.get<{ role: UserRole }>('/auth/profile')
        .then(res => setRole(res.data.role))
        .catch(() => {
          localStorage.removeItem('token')
          delete api.defaults.headers.common.Authorization
        })
    }

    // Wallet auto‐reconnect
    const eth = (window as any).ethereum
    if (eth) {
      const manuallyDisconnected = localStorage.getItem('manualDisconnect') === 'true'
      if (!manuallyDisconnected) {
        eth.request({ method: 'eth_accounts' })
          .then((accounts: string[]) => accounts[0] && setAccount(accounts[0]))
          .catch(console.error)
      }

      // Watch for account changes
      const onAccountsChanged = (accounts: string[]) => {
        if (accounts.length === 0) {
          handleDisconnect()
        } else if (!manuallyDisconnected) {
          setAccount(accounts[0])
        }
      }
      eth.on('accountsChanged', onAccountsChanged)
      return () => eth.removeListener('accountsChanged', onAccountsChanged)
    }
  }, [handleDisconnect])

  // Close sidebar on outside click (optional, if you want click outside to close)
  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (
        sidebarOpen &&
        wrapperRef.current &&
        !wrapperRef.current.contains(e.target as Node)
      ) {
        setSidebarOpen(false)
      }
    }
    document.addEventListener('mousedown', onClick)
    return () => {
      document.removeEventListener('mousedown', onClick)
    }
  }, [sidebarOpen])

  const shortAddr = account
    ? `${account.slice(0, 6)}…${account.slice(-4)}`
    : ''

  return (
    <>
      {/* Sidebar (slides in/out) */}
      <Sidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      <header
        className="sticky top-0 z-50 bg-background-header dark:bg-background-dark border-b border-border-light dark:border-gray-700"
        ref={wrapperRef}
      >
        <div className="max-w-7xl mx-auto flex h-16 items-center justify-between px-4">
          {/* ── Left: G.svg “hamburger” / sidebar toggle + Logo ──────── */}
          <div className="flex items-center space-x-4">
            <button
              onClick={() => setSidebarOpen(o => !o)}
              className="p-1 focus:outline-none"
            >
              <span className="sr-only">Open sidebar</span>
              <Image
                src="/G.svg"
                alt="Menu"
                width={24}
                height={24}
                className="text-text"
              />
            </button>
            <Link href="/" className="flex items-center">
              <Image
                src="/Stickeyai.svg"
                alt="Stickey.ai"
                width={144}
                height={48}
                priority
              />
            </Link>
          </div>

          {/* ── Right: Connect Wallet OR Account Pill ───────────────── */}
          <div className="flex items-center space-x-4">
            {!account ? (
              <button
                onClick={handleConnect}
                className="px-3 py-1 rounded border border-text text-text bg-transparent hover:bg-gray-100 dark:hover:bg-gray-800 transition text-sm"
              >
                Connect Wallet
              </button>
            ) : (
              <div className="relative">
                <button
                  onClick={() => {}}
                  className="px-3 py-1 rounded-full border border-text bg-transparent hover:bg-gray-100 dark:hover:bg-gray-800 transition text-sm"
                >
                  {shortAddr}
                </button>
                <div className="absolute right-0 mt-2 w-32 bg-white dark:bg-gray-800 border border-border-light dark:border-gray-700 rounded shadow-lg hidden">
                  <button
                    onClick={handleDisconnect}
                    className="w-full text-left px-4 py-2 hover:bg-gray-100 dark:hover:bg-gray-700 transition text-sm"
                  >
                    Disconnect
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </header>
    </>
  )
}