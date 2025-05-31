// frontend/components/Navbar.tsx
'use client'

import Link from 'next/link'
import Image from 'next/image'
import { useRouter } from 'next/navigation'
import { useEffect, useState, useRef, useCallback } from 'react'
import api from '@/lib/api'
import { UserRole } from '@/hooks/useAuthRedirect'
import { signInWithEthereum, logout } from '@/utils/auth'
// Note: We've removed the SwapBar import since we're integrating swap inputs directly here
// import SwapBar from './SwapBar'

export default function Navbar() {
  const router = useRouter()
  const [account, setAccount]           = useState<string | null>(null)
  const [role, setRole]                 = useState<UserRole | null>(null)
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const [sidebarOpen, setSidebarOpen]   = useState(false)
  const wrapperRef = useRef<HTMLDivElement>(null)

  //
  // 1) Handle “Connect Wallet”
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
  // 4) Close account dropdown on outside click
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

  // Swap amounts (for inline swap inputs)
  const [amountIn, setAmountIn]   = useState('')
  const [amountOut, setAmountOut] = useState('')

  return (
    <>
      {/* ─── Sidebar Toggle in Top-Left ───────────────────────────────────────── */}
      <button
        onClick={() => setSidebarOpen(true)}
        className="fixed top-4 left-4 p-2 border border-gray-200 dark:border-gray-700 rounded bg-white dark:bg-gray-900 z-50"
        aria-label="Open menu"
      >
        <Image
          src="/G.svg"
          alt="Menu"
          width={24}
          height={24}
        />
      </button>

      {/* ─── Top Bar / Navbar ─────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-40 bg-background-header dark:bg-background-dark border-b border-border-light dark:border-gray-700">
        <div className="max-w-7xl mx-auto flex h-16 items-center justify-between px-4">

          {/* ── (1) Left Group: Logo + Live Indicator ─────────────────────────── */}
          <div className="flex items-center space-x-4">
            {/* (1a) Logo (no border) */}
            <Link href="/" className="flex items-center -ml-2">
              <Image
                src="/Stickeyai.svg"
                alt="Stickey.ai"
                width={128}
                height={40}
                priority
              />
            </Link>

            {/* (1b) “Live” indicator with green dot */}
            <div className="flex items-center space-x-1">
              <span className="inline-block w-2 h-2 bg-green-500 rounded-full" />
              <span className="text-text font-medium">Live</span>
            </div>
          </div>

          {/* ── (2) Center: Search Bar ──────────────────────────────────────────── */}
          <div className="flex-1 flex justify-center px-4">
            <input
              type="text"
              placeholder="Search by title or category…"
              className="w-full max-w-md p-2 border border-gray-300 rounded-full focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* ── (3) Right Group: Inline Swap + Wallet ──────────────────────────── */}
          <div className="flex items-center space-x-2">
            {/* ─── Amount In Input ─── */}
            <input
              type="number"
              value={amountIn}
              onChange={(e) => setAmountIn(e.target.value)}
              placeholder="0"
              className="w-16 p-1 border border-gray-300 rounded text-center text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />

            {/* ─── From Token Button ─── */}
            <button
              type="button"
              className="flex items-center border border-gray-300 rounded px-1 py-1 text-sm hover:bg-gray-50"
              onClick={() => {/* open “from” token picker */}}
            >
              <Image src="/tokens/usdt.svg" alt="USDT" width={16} height={16} />
              <span className="ml-1">USDT</span>
            </button>

            {/* ─── Arrow Icon ─── */}
            <span className="text-xl text-gray-400 select-none">→</span>

            {/* ─── Amount Out Input ─── */}
            <input
              type="number"
              value={amountOut}
              onChange={(e) => setAmountOut(e.target.value)}
              placeholder="0"
              className="w-16 p-1 border border-gray-300 rounded text-center text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />

            {/* ─── To Token Button ─── */}
            <button
              type="button"
              className="flex items-center border border-gray-300 rounded px-1 py-1 text-sm hover:bg-gray-50"
              onClick={() => {/* open “to” token picker */}}
            >
              <Image src="/tokens/glu.svg" alt="GLU" width={16} height={16} />
              <span className="ml-1">$GLU</span>
            </button>

            {/* ─── Swap Button ─── */}
            <button
              onClick={() => router.push('/swap')}
              className="px-3 py-1 border border-text-primary rounded text-text-primary text-sm hover:bg-gray-100 transition"
            >
              Swap
            </button>

            {/* ─── Connect / Display Wallet ─── */}
            {!account ? (
              <button
                onClick={handleConnect}
                className="ml-2 px-3 py-1 border border-text-primary rounded text-text-primary text-sm hover:bg-gray-100 transition"
              >
                Connect Wallet
              </button>
            ) : (
              <div ref={wrapperRef} className="relative ml-2">
                <button
                  onClick={() => setDropdownOpen(o => !o)}
                  className="px-3 py-1 border border-text-primary rounded text-text-primary text-sm hover:bg-gray-100 transition"
                >
                  {shortAddr}
                </button>
                {dropdownOpen && (
                  <div className="absolute right-0 mt-2 w-40 bg-white dark:bg-gray-800 border border-border-light dark:border-gray-700 rounded shadow-lg">
                    <button
                      onClick={handleDisconnect}
                      className="w-full text-left px-4 py-2 text-text-primary hover:bg-gray-100 dark:hover:bg-gray-700 transition text-sm"
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