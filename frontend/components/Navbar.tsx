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

  // Inline swap amounts (shown in desktop header)
  const [amountIn, setAmountIn]   = useState('')
  const [amountOut, setAmountOut] = useState('')

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

      {/* ─── Top Bar / Navbar ────────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-40 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto flex items-center justify-between h-16 px-4">
          
          {/* ── (1) Left: “G” Toggle + Logo ──────────────────────────────────────────── */}
          <div className="flex items-center space-x-4">
            {/* “G” Toggle */}
            <button
              onClick={() => setSidebarOpen(true)}
              className="
                p-2
                border border-gray-300 dark:border-gray-700
                rounded-lg
                bg-white dark:bg-gray-900
                flex-shrink-0
                focus:outline-none
                transition
              "
              aria-label="Open menu"
            >
              <Image src="/G.svg" alt="Menu" width={24} height={24} />
            </button>

            {/* Stickey.ai Logo (no border) */}
            <Link href="/" className="flex items-center">
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

          {/* ── (2) Center: Search + Swap (desktop only) ───────────────────────────────── */}
          <div className="hidden md:flex flex-1 justify-center items-center space-x-3">
            {/* Search Input */}
            <input
              type="text"
              placeholder="Search by title or category…"
              className="
                w-full max-w-lg
                py-2 px-3
                border border-black dark:border-white
                rounded-lg
                text-sm text-gray-800 dark:text-gray-100
                focus:outline-none focus:ring-2 focus:ring-blue-500
                bg-white dark:bg-gray-900
              "
            />

            {/* Amount In Input */}
            <input
              type="number"
              value={amountIn}
              onChange={(e) => setAmountIn(e.target.value)}
              placeholder="0"
              className="
                w-24 sm:w-32
                py-2 px-2
                border border-black dark:border-white
                rounded-lg
                text-center text-sm text-gray-800 dark:text-gray-100
                focus:outline-none focus:ring-2 focus:ring-blue-500
                bg-white dark:bg-gray-900
              "
            />

            {/* From Token Selector */}
            <button
              type="button"
              className="
                flex items-center
                border border-black dark:border-white
                rounded-lg
                py-2 px-3
                bg-white dark:bg-gray-900
                text-sm text-gray-800 dark:text-gray-100
                hover:bg-gray-100 dark:hover:bg-gray-700
                focus:outline-none
                transition
              "
              onClick={() => { /* open “from” token picker */ }}
            >
              <Image src="/tokens/usdt.svg" alt="USDT" width={16} height={16} />
              <span className="ml-1">USDT</span>
            </button>

            {/* Arrow Icon */}
            <span className="text-lg text-gray-400 select-none">→</span>

            {/* Amount Out Input */}
            <input
              type="number"
              value={amountOut}
              onChange={(e) => setAmountOut(e.target.value)}
              placeholder="0"
              className="
                w-24 sm:w-32
                py-2 px-2
                border border-black dark:border-white
                rounded-lg
                text-center text-sm text-gray-800 dark:text-gray-100
                focus:outline-none focus:ring-2 focus:ring-blue-500
                bg-white dark:bg-gray-900
              "
            />

            {/* To Token Selector */}
            <button
              type="button"
              className="
                flex items-center
                border border-black dark:border-white
                rounded-lg
                py-2 px-3
                bg-white dark:bg-gray-900
                text-sm text-gray-800 dark:text-gray-100
                hover:bg-gray-100 dark:hover:bg-gray-700
                focus:outline-none
                transition
              "
              onClick={() => { /* open “to” token picker */ }}
            >
              <Image src="/tokens/glu.svg" alt="GLU" width={16} height={16} />
              <span className="ml-1">$GLU</span>
            </button>

            {/* Swap Button */}
            <button
              onClick={() => router.push('/swap')}
              className="
                py-2 px-4
                border border-black dark:border-white
                rounded-lg
                bg-transparent
                text-black dark:text-white
                text-sm
                hover:bg-gray-100 dark:hover:bg-gray-700
                focus:outline-none
                transition
              "
            >
              Swap
            </button>
          </div>

          {/* ── (3) Right: Live Indicator + Wallet ────────────────────────────────────── */}
          <div className="flex items-center space-x-4">
            {/* “Live” Indicator (clickable) */}
            <button
              onClick={() => router.push('/products')}
              className="
                flex items-center space-x-1
                py-2 px-4
                border border-black dark:border-white
                rounded-lg
                bg-transparent
                text-black dark:text-white
                text-sm
                hover:bg-gray-100 dark:hover:bg-gray-700
                focus:outline-none
                transition
              "
            >
              <span className="inline-block w-2 h-2 bg-green-500 rounded-full" />
              <span className="font-medium">Live</span>
            </button>

            {/* Wallet / Connect Wallet */}
            {!account ? (
              <button
                onClick={handleConnect}
                className="
                  py-2 px-4
                  border border-black dark:border-white
                  rounded-lg
                  bg-transparent
                  text-black dark:text-white
                  text-sm
                  hover:bg-gray-100 dark:hover:bg-gray-700
                  focus:outline-none
                  transition
                "
              >
                Connect Wallet
              </button>
            ) : (
              <div ref={wrapperRef} className="relative">
                <button
                  onClick={() => setDropdownOpen(o => !o)}
                  className="
                    py-2 px-4
                    border border-black dark:border-white
                    rounded-lg
                    bg-transparent
                    text-black dark:text-white
                    text-sm
                    hover:bg-gray-100 dark:hover:bg-gray-700
                    focus:outline-none
                    transition
                  "
                >
                  {shortAddr}
                </button>
                {dropdownOpen && (
                  <div className="
                    absolute right-0 mt-2 w-40
                    bg-white dark:bg-gray-800
                    border border-gray-200 dark:border-gray-700
                    rounded-lg shadow-lg
                    z-50
                  ">
                    <button
                      onClick={handleDisconnect}
                      className="
                        w-full text-left px-4 py-2
                        text-gray-800 dark:text-gray-200
                        text-sm
                        hover:bg-gray-100 dark:hover:bg-gray-700
                        focus:outline-none
                        transition
                      "
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