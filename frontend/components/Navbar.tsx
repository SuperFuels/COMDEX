// frontend/components/Navbar.tsx
'use client'

import Link from 'next/link'
import Image from 'next/image'
import { useRouter } from 'next/navigation'
import { useEffect, useState, useRef, useCallback } from 'react'
import api from '@/lib/api'
import { UserRole } from '@/hooks/useAuthRedirect'
import { signInWithEthereum, logout } from '@/utils/auth'
import Sidebar from './Sidebar'

export default function Navbar() {
  const router = useRouter()
  const [account, setAccount]           = useState<string | null>(null)
  const [role, setRole]                 = useState<UserRole | null>(null)
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const [sidebarOpen, setSidebarOpen]   = useState(false)
  const wrapperRef = useRef<HTMLDivElement>(null)

  //
  // 1) Handle “Connect Wallet” (SIWE)
  //
  const handleConnect = useCallback(async () => {
    localStorage.removeItem('manualDisconnect')
    try {
      const { address, role: newRole } = await signInWithEthereum()
      setAccount(address)
      setRole(newRole as UserRole)
    } catch (err: any) {
      console.error('SIWE login failed', err)
      if (err.response?.status === 404) {
        router.push('/register')
      }
    }
  }, [router])

  //
  // 2) Handle “Disconnect / Logout”
  //
  const handleDisconnect = useCallback(() => {
    localStorage.setItem('manualDisconnect', 'true')
    logout()
    setAccount(null)
    setRole(null)
    setDropdownOpen(false)
    router.push('/')
  }, [router])

  //
  // 3) On‐mount: hydrate JWT and/or wallet
  //
  useEffect(() => {
    // a) If a JWT exists, retrieve role
    const token = localStorage.getItem('token')
    if (token) {
      api.defaults.headers.common.Authorization = `Bearer ${token}`
      api
        .get<{ role: UserRole }>('/auth/profile')
        .then(res => setRole(res.data.role))
        .catch(() => {
          localStorage.removeItem('token')
          delete api.defaults.headers.common.Authorization
        })
    }

    // b) Wallet auto‐reconnect
    const eth = (window as any).ethereum
    if (eth) {
      const manuallyDisconnected = localStorage.getItem('manualDisconnect') === 'true'
      if (!manuallyDisconnected) {
        eth
          .request({ method: 'eth_accounts' })
          .then((accounts: string[]) => {
            if (accounts.length > 0) {
              setAccount(accounts[0])
            }
          })
          .catch(console.error)
      }

      // c) Watch for account changes
      const onAccountsChanged = (accounts: string[]) => {
        if (accounts.length === 0) {
          handleDisconnect()
        } else if (!manuallyDisconnected) {
          setAccount(accounts[0])
        }
      }
      eth.on('accountsChanged', onAccountsChanged)
      return () => {
        eth.removeListener('accountsChanged', onAccountsChanged)
      }
    }
  }, [handleDisconnect])

  //
  // 4) Close the connected‐account dropdown if clicked outside
  //
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (
        dropdownOpen &&
        wrapperRef.current &&
        !wrapperRef.current.contains(e.target as Node)
      ) {
        setDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [dropdownOpen])

  // Shorten the address for display (e.g. 0x1234…abcd)
  const shortAddr = account
    ? `${account.slice(0, 6)}…${account.slice(-4)}`
    : ''

  // Determine dashboard path by role
  const dashboardPath =
    role === 'admin'    ? '/admin/dashboard'    :
    role === 'supplier' ? '/supplier/dashboard' :
    role === 'buyer'    ? '/buyer/dashboard'    :
    undefined

  return (
    <>
      {/* ─── Slide‐in Sidebar ─────────────────────────────────────────────── */}
      <Sidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        role={role}
        account={account}
        onLogout={handleDisconnect}
      />

      {/* ─── Top Bar / Navbar ────────────────────────────────────────────── */}
      <header className="sticky top-0 z-50 bg-background-header dark:bg-background-dark border-b border-border-light">
        <div className="max-w-7xl mx-auto flex h-16 items-center justify-between px-4">
          {/* ── (1) Left: “G.svg” toggle / Logo / “Live” indicator ────────── */}
          <div className="flex items-center space-x-4">
            {/* (1a) “G.svg” toggle */}
            <button
              onClick={() => setSidebarOpen(true)}
              className="p-2 focus:outline-none"
              aria-label="Open menu"
            >
              <Image
                src="/G.svg"
                alt="Menu"
                width={24}
                height={24}
              />
            </button>

            {/* (1b) Logo (no border) */}
            <Link href="/" className="flex items-center">
              <Image
                src="/Stickeyai.svg"
                alt="Stickey.ai"
                width={144}
                height={48}
                priority
              />
            </Link>

            {/* (1c) “Live” indicator with green dot */}
            <Link href="/" className="flex items-center space-x-1">
              <span className="inline-block w-2 h-2 bg-green-500 rounded-full" />
              <span className="text-text font-medium">Live</span>
            </Link>
          </div>

          {/* ── (2) Center: (empty or placeholder for search/swap) ───────────── */}
          <div className="flex-1 flex justify-center">
            {/* If you want a search input or a SwapBar here, put it inside this div */}
            {/* e.g. <SwapBar /> */}
          </div>

          {/* ── (3) Right: Wallet UI only ──────────────────────────────────── */}
          <div className="flex items-center space-x-4">
            {!account ? (
              // (3a) If not connected: show “Connect Wallet” button
              <button
                onClick={handleConnect}
                className="px-3 py-1 border border-text-primary rounded text-text-primary hover:bg-gray-100 transition"
              >
                Connect Wallet
              </button>
            ) : (
              // (3b) If connected: show short address + dropdown
              <div ref={wrapperRef} className="relative">
                <button
                  onClick={() => setDropdownOpen(o => !o)}
                  className="px-3 py-1 border border-text-primary rounded text-text-primary hover:bg-gray-100 transition"
                >
                  {shortAddr}
                </button>
                {dropdownOpen && (
                  <div className="absolute right-0 mt-2 w-40 bg-white dark:bg-gray-800 border border-border-light dark:border-gray-700 rounded shadow-lg">
                    <button
                      onClick={handleDisconnect}
                      className="w-full text-left px-4 py-2 text-text-primary hover:bg-gray-100 dark:hover:bg-gray-700 transition"
                    >
                      Disconnect
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </header>
    </>
  )
}