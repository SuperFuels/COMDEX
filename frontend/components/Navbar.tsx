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
import { DarkModeToggle } from './DarkModeToggle'

export default function Navbar() {
  const router = useRouter()
  const [account, setAccount] = useState<string | null>(null)
  const [role, setRole] = useState<UserRole | null>(null)
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const wrapperRef = useRef<HTMLDivElement>(null)

  const handleConnect = useCallback(async () => {
    if (typeof window === 'undefined') return
    localStorage.removeItem('manualDisconnect')
    try {
      const { address, role: newRole } = await signInWithEthereum()
      setAccount(address)
      setRole(newRole as UserRole)
    } catch (err: any) {
      console.error('SIWE login failed', err)
      if (err?.response?.status === 404) router.push('/register')
    }
  }, [router])

  const handleDisconnect = useCallback(() => {
    if (typeof window === 'undefined') return
    localStorage.setItem('manualDisconnect', 'true')
    logout()
    setAccount(null)
    setRole(null)
    setDropdownOpen(false)
    router.push('/')
  }, [router])

  // bootstrap auth + wallet
  useEffect(() => {
    if (typeof window === 'undefined') return

    const token = localStorage.getItem('token')
    if (token) {
      api.defaults.headers.common.Authorization = `Bearer ${token}`
      api
        .get<{ role: UserRole }>('/auth/profile')
        .then(res => setRole(res.data.role))
        .catch(() => {
          localStorage.removeItem('token')
          delete (api.defaults.headers.common as any).Authorization
        })
    }

    const eth = (window as any).ethereum
    if (!eth) return

    const manuallyDisconnected = localStorage.getItem('manualDisconnect') === 'true'
    if (!manuallyDisconnected) {
      eth
        .request({ method: 'eth_accounts' })
        .then((accounts: string[]) => accounts[0] && setAccount(accounts[0]))
        .catch(console.error)
    }

    const onAccountsChanged = (accounts: string[]) => {
      if (accounts.length === 0) handleDisconnect()
      else if (!manuallyDisconnected) setAccount(accounts[0])
    }
    eth.on('accountsChanged', onAccountsChanged)
    return () => eth.removeListener('accountsChanged', onAccountsChanged)
  }, [handleDisconnect])

  // close wallet menu on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownOpen && wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [dropdownOpen])

  const shortAddr = account ? `${account.slice(0, 6)}…${account.slice(-4)}` : ''
  const [amountIn, setAmountIn] = useState('')
  const [amountOut, setAmountOut] = useState('')

  return (
    <>
      <Sidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        role={role}
        account={account}
        onLogout={handleDisconnect}
      />

      {/* Sidebar toggle */}
      <button
        onClick={() => setSidebarOpen(true)}
        className="fixed top-4 left-4 z-50 rounded-lg border border-border bg-background px-2 py-2"
        aria-label="Open menu"
      >
        <Image src="/G.svg" alt="Menu" width={24} height={24} />
      </button>

      <header className="sticky top-0 z-40 border-b border-border bg-background">
        <div className="flex h-16 items-center justify-between gap-4 px-4">
          {/* Logo */}
          <div className="ml-12 flex items-center">
            <Link href="/" className="logo-link flex items-center">
              <Image
                src="/Stickeyai.svg"
                alt="Stickey.ai"
                width={128}
                height={40}
                priority
                className="border-none"
              />
            </Link>
          </div>

          {/* Swap strip */}
          <div className="flex flex-1 justify-center">
            <div className="flex items-center gap-2">
              <input
                type="number"
                inputMode="decimal"
                value={amountIn}
                onChange={e => setAmountIn(e.target.value)}
                placeholder="0"
                className="w-24 sm:w-28 rounded-lg border border-border bg-background px-2 py-1 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring/30"
              />
              <button
                type="button"
                className="flex items-center rounded-lg border border-border bg-background px-2 py-1 text-sm hover:bg-muted/50"
              >
                <Image src="/tokens/usdt.svg" alt="USDT" width={16} height={16} />
                <span className="ml-1">USDT</span>
              </button>
              <span className="select-none text-lg text-muted-foreground">→</span>
              <input
                type="number"
                inputMode="decimal"
                value={amountOut}
                onChange={e => setAmountOut(e.target.value)}
                placeholder="0"
                className="w-24 sm:w-28 rounded-lg border border-border bg-background px-2 py-1 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring/30"
              />
              <button
                type="button"
                className="flex items-center rounded-lg border border-border bg-background px-2 py-1 text-sm hover:bg-muted/50"
              >
                <Image src="/tokens/glu.svg" alt="GLU" width={16} height={16} />
                <span className="ml-1">$GLU</span>
              </button>
              <button
                onClick={() => router.push('/swap')}
                className="rounded-lg border border-border bg-transparent px-3 py-1 text-sm text-foreground hover:bg-muted/50"
              >
                Swap
              </button>
            </div>
          </div>

          {/* Right: dark toggle + wallet */}
          <div className="flex items-center gap-3">
            <DarkModeToggle />
            {!account ? (
              <button
                onClick={handleConnect}
                className="rounded-lg border border-border bg-transparent px-3 py-1 text-sm text-foreground hover:bg-muted/50"
              >
                Connect Wallet
              </button>
            ) : (
              <div ref={wrapperRef} className="relative">
                <button
                  onClick={() => setDropdownOpen(o => !o)}
                  className="rounded-lg border border-border bg-transparent px-3 py-1 text-sm text-foreground hover:bg-muted/50"
                >
                  {shortAddr}
                </button>
                {dropdownOpen && (
                  <div className="absolute right-0 mt-2 w-40 rounded-lg border border-border bg-background shadow-lg">
                    <button
                      onClick={handleDisconnect}
                      className="w-full px-4 py-2 text-left text-sm hover:bg-muted/50"
                    >
                      Logout
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