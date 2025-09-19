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

  const handleDisconnect = useCallback(() => {
    localStorage.setItem('manualDisconnect', 'true')
    logout()
    setAccount(null)
    setRole(null)
    setDropdownOpen(false)
    router.push('/')
  }, [router])

  useEffect(() => {
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
      eth.request({ method: 'eth_accounts' })
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
        className="fixed top-4 left-4 p-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 z-50"
        aria-label="Open menu"
      >
        <Image src="/G.svg" alt="Menu" width={24} height={24} />
      </button>

      <header className="sticky top-0 z-40 bg-background border-b border-border">
        <div className="flex items-center justify-between h-16 px-4 gap-4">
          {/* Logo */}
          <div className="flex items-center ml-12">
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

          {/* Swap strip (center) */}
          <div className="flex-1 flex justify-center">
            <div className="flex items-center gap-2">
              <input
                type="number"
                value={amountIn}
                onChange={e => setAmountIn(e.target.value)}
                placeholder="0"
                className="w-24 sm:w-28 py-1 px-2 border border-gray-300 dark:border-gray-600 rounded-lg text-center text-sm bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                type="button"
                className="flex items-center border border-gray-300 dark:border-gray-600 rounded-lg py-1 px-2 bg-white dark:bg-gray-800 text-sm hover:bg-gray-50 dark:hover:bg-gray-700"
              >
                <Image src="/tokens/usdt.svg" alt="USDT" width={16} height={16} />
                <span className="ml-1">USDT</span>
              </button>
              <span className="text-lg text-gray-400 select-none">→</span>
              <input
                type="number"
                value={amountOut}
                onChange={e => setAmountOut(e.target.value)}
                placeholder="0"
                className="w-24 sm:w-28 py-1 px-2 border border-gray-300 dark:border-gray-600 rounded-lg text-center text-sm bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                type="button"
                className="flex items-center border border-gray-300 dark:border-gray-600 rounded-lg py-1 px-2 bg-white dark:bg-gray-800 text-sm hover:bg-gray-50 dark:hover:bg-gray-700"
              >
                <Image src="/tokens/glu.svg" alt="GLU" width={16} height={16} />
                <span className="ml-1">$GLU</span>
              </button>
              <button
                onClick={() => router.push('/swap')}
                className="py-1 px-3 border border-black rounded-lg bg-transparent text-sm hover:bg-gray-100 dark:hover:bg-gray-700"
              >
                Swap
              </button>
            </div>
          </div>

          {/* Right: Dark toggle + Connect */}
          <div className="flex items-center gap-3">
            <DarkModeToggle />

            {!account ? (
              <button
                onClick={handleConnect}
                className="py-1 px-3 border border-black rounded-lg bg-transparent text-sm hover:bg-gray-100 dark:hover:bg-gray-700"
              >
                Connect Wallet
              </button>
            ) : (
              <div ref={wrapperRef} className="relative">
                <button
                  onClick={() => setDropdownOpen(o => !o)}
                  className="py-1 px-3 border border-black rounded-lg bg-transparent text-sm hover:bg-gray-100 dark:hover:bg-gray-700"
                >
                  {shortAddr}
                </button>
                {dropdownOpen && (
                  <div className="absolute right-0 mt-2 w-40 bg-white dark:bg-gray-800 border border-border rounded-lg shadow-lg z-50">
                    <button
                      onClick={handleDisconnect}
                      className="w-full text-left px-4 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-700"
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