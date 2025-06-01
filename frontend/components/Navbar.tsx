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

  // Inline swap amounts (desktop only)
  const [amountIn, setAmountIn]   = useState('')
  const [amountOut, setAmountOut] = useState('')

  return (
    <>
      {/* ─── (A) Full‐Width Top Bar: “G” + (flush‐right) Live & Wallet ───────────── */}
      <div className="fixed inset-x-0 top-0 z-50 bg-background-header dark:bg-background-dark border-b border-border-light dark:border-gray-700 h-16 flex items-center">
        {/* ‣ (A1) “G” Toggle on the far left */}
        <button
          onClick={() => setSidebarOpen(true)}
          className="
            ml-4
            p-2
            border border-gray-300 dark:border-gray-700
            rounded-lg
            bg-white dark:bg-gray-900
            focus:outline-none
          "
          aria-label="Open menu"
        >
          <Image src="/G.svg" alt="Menu" width={24} height={24} />
        </button>

        {/* ‣ (A2) Spacer to push the right items flush to the far right */}
        <div className="flex-grow" />

        {/* ‣ (A3) “Live” + “Connect Wallet” flush-right */}
        <div className="flex items-center space-x-3 mr-4">
          {/* “Live” Indicator (black border) */}
          <div className="flex items-center space-x-1 border border-black rounded-lg py-1 px-3">
            <span className="inline-block w-2 h-2 bg-green-500 rounded-full" />
            <span className="text-text font-medium text-sm">Live</span>
          </div>

          {/* Wallet / Connect Wallet */}
          {!account ? (
            <button
              onClick={handleConnect}
              className="
                py-1 px-4
                border border-black
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
                  py-1 px-4
                  border border-black
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
                  border border-border-light dark:border-gray-700
                  rounded-lg shadow-lg
                  z-50
                ">
                  <button
                    onClick={handleDisconnect}
                    className="
                      w-full text-left px-4 py-2
                      text-text-primary dark:text-text-secondary
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

      {/* ─── (B) Centered Second Row: Logo + (desktop) Search/Swap ───────────────── */}
      <header className="pt-16 z-40">
        <div className="max-w-7xl mx-auto flex items-center justify-between h-16 px-4">
          {/* ‣ (B1) Logo, shifted right by ~15px via extra padding */}
          <div className="flex items-center pl-4">
            <Link href="/" className="logo-link flex items-center">
              <Image
                src="/Stickeyai.svg"
                alt="Stickey.ai"
                width={128}
                height={40}
                priority
              />
            </Link>
          </div>

          {/* ‣ (B2) Desktop Search + Swap (centered) */}
          <div className="hidden md:flex flex-1 justify-center items-center space-x-4 px-4">
            {/* Search Input (rounded-lg, reduced height) */}
            <input
              type="text"
              placeholder="Search by title or category…"
              className="
                w-full max-w-lg
                py-1.5 px-3
                border border-gray-300 dark:border-gray-600
                rounded-lg
                text-sm text-text
                bg-white dark:bg-gray-800
                focus:outline-none focus:ring-2 focus:ring-blue-500
              "
            />

            {/* Amount In Input */}
            <input
              type="number"
              value={amountIn}
              onChange={(e) => setAmountIn(e.target.value)}
              placeholder="0"
              className="
                w-20 sm:w-28
                py-1 px-2
                border border-gray-300 dark:border-gray-600
                rounded-lg
                text-center text-sm
                bg-white dark:bg-gray-800
                focus:outline-none focus:ring-2 focus:ring-blue-500
              "
            />

            {/* From Token Selector */}
            <button
              type="button"
              className="
                flex items-center
                border border-gray-300 dark:border-gray-600
                rounded-lg
                py-1 px-3
                bg-white dark:bg-gray-800
                text-sm text-text
                hover:bg-gray-50 dark:hover:bg-gray-700
                focus:outline-none
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
                w-20 sm:w-28
                py-1 px-2
                border border-gray-300 dark:border-gray-600
                rounded-lg
                text-center text-sm
                bg-white dark:bg-gray-800
                focus:outline-none focus:ring-2 focus:ring-blue-500
              "
            />

            {/* To Token Selector */}
            <button
              type="button"
              className="
                flex items-center
                border border-gray-300 dark:border-gray-600
                rounded-lg
                py-1 px-3
                bg-white dark:bg-gray-800
                text-sm text-text
                hover:bg-gray-50 dark:hover:bg-gray-700
                focus:outline-none
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
                py-1 px-4
                border border-black
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

          {/* ‣ (B3) Empty spacer on right so the centered content doesn’t bump into anything */}
          <div className="w-16" />
        </div>
      </header>

      {/* ─── (C) Lower Swap Bar for Mobile Only ───────────────────────────────── */}
      <div className="md:hidden sticky top-16 z-30 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 py-2 flex items-center space-x-2">
          {/* Mobile Search Input */}
          <input
            type="text"
            placeholder="Search by title or category…"
            className="
              flex-1
              py-1 px-2
              border border-gray-300 dark:border-gray-600
              rounded-lg
              text-sm text-text
              bg-white dark:bg-gray-800
              focus:outline-none focus:ring-2 focus:ring-blue-500
            "
          />

          {/* Mobile Amount In Input */}
          <input
            type="number"
            value={amountIn}
            onChange={(e) => setAmountIn(e.target.value)}
            placeholder="0"
            className="
              w-16
              py-1 px-1
              border border-gray-300 dark:border-gray-600
              rounded-lg
              text-center text-sm text-text
              bg-white dark:bg-gray-800
              focus:outline-none focus:ring-2 focus:ring-blue-500
            "
          />

          {/* Mobile “From” Token */}
          <button
            type="button"
            className="
              flex items-center
              border border-gray-300 dark:border-gray-600
              rounded-lg
              py-1 px-2
              bg-white dark:bg-gray-800
              text-sm text-text
              hover:bg-gray-50 dark:hover:bg-gray-700
              focus:outline-none
            "
            onClick={() => { /* open “from” token picker */ }}
          >
            <Image src="/tokens/usdt.svg" alt="USDT" width={16} height={16} />
            <span className="ml-1">USDT</span>
          </button>

          {/* Mobile Arrow */}
          <span className="text-xl text-gray-400 select-none">→</span>

          {/* Mobile Amount Out Input */}
          <input
            type="number"
            value={amountOut}
            onChange={(e) => setAmountOut(e.target.value)}
            placeholder="0"
            className="
              w-16
              py-1 px-1
              border border-gray-300 dark:border-gray-600
              rounded-lg
              text-center text-sm text-text
              bg-white dark:bg-gray-800
              focus:outline-none focus:ring-2 focus:ring-blue-500
            "
          />

          {/* Mobile “To” Token */}
          <button
            type="button"
            className="
              flex items-center
              border border-gray-300 dark:border-gray-600
              rounded-lg
              py-1 px-2
              bg-white dark:bg-gray-800
              text-sm text-text
              hover:bg-gray-50 dark:hover:bg-gray-700
              focus:outline-none
            "
            onClick={() => { /* open “to” token picker */ }}
          >
            <Image src="/tokens/glu.svg" alt="GLU" width={16} height={16} />
            <span className="ml-1">$GLU</span>
          </button>

          {/* Mobile Swap Button */}
          <button
            onClick={() => router.push('/swap')}
            className="
              py-1 px-3
              border border-black
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
      </div>
    </>
  )
}