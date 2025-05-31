// frontend/components/Navbar.tsx
'use client'
import Link from 'next/link'
import Image from 'next/image'
import { useRouter } from 'next/navigation'       // ← import from "next/navigation"
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

  // SIWE login via wallet
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

  // Manual logout
  const handleDisconnect = useCallback(() => {
    localStorage.setItem('manualDisconnect', 'true')
    logout()
    setAccount(null)
    setRole(null)
    setDropdownOpen(false)
    router.push('/')
  }, [router])

  // Hydrate JWT and/or wallet on mount
  useEffect(() => {
    // 1) JWT
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

    // 2) Wallet auto-reconnect
    const eth = (window as any).ethereum
    if (eth) {
      const manuallyDisconnected = localStorage.getItem('manualDisconnect') === 'true'
      if (!manuallyDisconnected) {
        eth.request({ method: 'eth_accounts' })
           .then((accounts: string[]) => accounts[0] && setAccount(accounts[0]))
           .catch(console.error)
      }
      // 3) Watch for account changes
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

  // Close account dropdown on outside click
  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (
        dropdownOpen &&
        wrapperRef.current &&
        !wrapperRef.current.contains(e.target as Node)
      ) {
        setDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [dropdownOpen])

  const shortAddr = account
    ? `${account.slice(0, 6)}…${account.slice(-4)}`
    : ''

  // Build dashboard link by role
  const dashboardPath =
    role === 'admin'    ? '/admin/dashboard'    :
    role === 'supplier' ? '/supplier/dashboard' :
    role === 'buyer'    ? '/buyer/dashboard'    :
    undefined

  return (
    <>
      {/* ─── Sidebar (sliding panel) ──────────────────────────────────── */}
      <Sidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      <header className="sticky top-0 bg-background-header dark:bg-background-dark border-b z-50">
        <div className="max-w-7xl mx-auto flex h-16 items-center justify-between px-4">
          {/* ─── 1) Hamburger Icon (far left) ────────────────────────── */}
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
              className="block"
            />
          </button>

          {/* ─── 2) Logo (center-left) ───────────────────────────────── */}
          <Link href="/" className="flex items-center">
            <Image
              src="/Stickeyai.svg"
              alt="Stickey.ai"
              width={144}
              height={48}
              priority
            />
          </Link>

          {/* ─── 3) Nav Links + Connect Wallet (far right) ───────────── */}
          <div className="flex items-center space-x-6">
            <Link href="/" className="text-text hover:text-primary transition">
              Marketplace
            </Link>

            {/* Unauthenticated Links */}
            {!account && !role && (
              <>
                <Link href="/register" className="text-text hover:text-primary transition">
                  Register
                </Link>
                <Link href="/login" className="text-text hover:text-primary transition">
                  Login
                </Link>
              </>
            )}

            {/* Role‐based Dashboard Link */}
            {dashboardPath && (
              <Link
                href={dashboardPath}
                className="text-text hover:text-primary transition"
              >
                {role![0].toUpperCase() + role!.slice(1)} Dashboard
              </Link>
            )}

            {/* ─── Connect vs. Account Pill ───────────────────────────── */}
            {!account ? (
              <button
                onClick={handleConnect}
                className="px-3 py-1 border border-text rounded text-text hover:bg-gray-100 transition"
              >
                Connect Wallet
              </button>
            ) : (
              <div ref={wrapperRef} className="relative">
                <button
                  onClick={() => setDropdownOpen((o) => !o)}
                  className="px-3 py-1 border border-text rounded text-text hover:bg-gray-100 transition"
                >
                  {shortAddr}
                </button>
                {dropdownOpen && (
                  <div className="absolute right-0 mt-2 w-40 bg-white border rounded shadow-lg">
                    <button
                      onClick={handleDisconnect}
                      className="w-full text-left px-4 py-2 hover:bg-gray-100 transition"
                    >
                      Disconnect
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* Note: DarkModeToggle has moved inside Sidebar, so we omit it here */}
          </div>
        </div>
      </header>
    </>
  )
}