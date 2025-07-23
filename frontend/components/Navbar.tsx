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
      if (err.response?.status === 404) {
        router.push('/register')
      }
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

  const shortAddr = account
    ? `${account.slice(0, 6)}…${account.slice(-4)}`
    : ''

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

      <button
        onClick={() => setSidebarOpen(true)}
        className="fixed top-4 left-4 p-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 z-50"
        aria-label="Open menu"
      >
        <Image src="/G.svg" alt="Menu" width={24} height={24} />
      </button>

      <header className="sticky top-0 z-40 bg-background-header dark:bg-background-dark border-b border-border-light dark:border-gray-700 h-16">
        <div className="flex items-center justify-between h-full px-4">
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

          <div className="flex-1 flex justify-center">
            <div className="flex items-center space-x-2">
              <input
                type="number"
                value={amountIn}
                onChange={e => setAmountIn(e.target.value)}
                placeholder="0"
                className="w-24 sm:w-28 py-1 px-2 border border-gray-300 dark:border-gray-600 rounded-lg text-center text-sm bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                type="button"
                className="flex items-center border border-gray-300 dark:border-gray-600 rounded-lg py-1 px-2 bg-white dark:bg-gray-800 text-sm text-text hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none"
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
                className="flex items-center border border-gray-300 dark:border-gray-600 rounded-lg py-1 px-2 bg-white dark:bg-gray-800 text-sm text-text hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none"
              >
                <Image src="/tokens/glu.svg" alt="GLU" width={16} height={16} />
                <span className="ml-1">$GLU</span>
              </button>
              <button
                onClick={() => router.push('/swap')}
                className="py-1 px-3 border border-black rounded-lg bg-transparent text-black dark:text-white text-sm hover:bg-gray-100 dark:hover:bg-gray-700 focus:outline-none transition"
              >
                Swap
              </button>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            {/* ✅ Container Map */}
              <Link
                href="aion/ContainerMap"
                className="flex items-center space-x-1 py-1 px-3 border border-purple-500 text-purple-600 rounded-lg bg-white dark:bg-gray-900 text-sm hover:bg-purple-50 dark:hover:bg-gray-800 focus:outline-none transition"
              >
                <Image src="/cube.svg" alt="Map" width={16} height={16} />
                <span>Map</span>
              </Link>

            <Link
              href="/aion/codex-playground"
              className="flex items-center space-x-1 py-1 px-3 border border-blue-600 text-blue-700 rounded-lg bg-white dark:bg-gray-900 text-sm hover:bg-blue-50 dark:hover:bg-gray-800 focus:outline-none transition"
            >
              <Image src="/scroll.svg" alt="Playground" width={16} height={16} />
              <span>Playground</span>
            </Link>

            <Link
              href="/aion/glyphnet"
              className="flex items-center space-x-1 py-1 px-3 border border-green-600 text-green-700 rounded-lg bg-white dark:bg-gray-900 text-sm hover:bg-green-50 dark:hover:bg-gray-800 focus:outline-none transition"
            >
              <Image src="/glyphnet.svg" alt="GlyphNet" width={16} height={16} />
              <span>GlyphNet</span>
            </Link>

            <Link
              href="/aion/multiverse"
              className="flex items-center space-x-1 py-1 px-3 border border-purple-500 text-purple-600 rounded-lg bg-white dark:bg-gray-900 text-sm hover:bg-purple-50 dark:hover:bg-gray-800 focus:outline-none transition"
            >
              <Image src="/universe.svg" alt="Multiverse" width={16} height={16} />
              <span>Multiverse</span>
            </Link>

            {/* ✅ Avatar Runtime */}
            <Link
              href="/aion/avatar-runtime"
              className="flex items-center space-x-1 py-1 px-3 border border-blue-500 text-blue-600 rounded-lg bg-white dark:bg-gray-900 text-sm hover:bg-blue-50 dark:hover:bg-gray-800 focus:outline-none transition"
            >
              <Image src="/avatar.svg" alt="Avatar Runtime" width={16} height={16} />
              <span>Runtime</span>
            </Link>

            {/* ✅ Codex HUD */}
            <Link
              href="/aion/codex-hud"
              className="flex items-center space-x-1 py-1 px-3 border border-red-500 text-red-600 rounded-lg bg-white dark:bg-gray-900 text-sm hover:bg-red-50 dark:hover:bg-gray-800 focus:outline-none transition"
            >
              <Image src="/hud.svg" alt="HUD" width={16} height={16} />
              <span>Codex HUD</span>
            </Link>

            <button
              onClick={() => router.push('/products')}
              className="flex items-center space-x-1 py-1 px-3 border border-black rounded-lg bg-transparent text-black dark:text-white text-sm hover:bg-gray-100 dark:hover:bg-gray-700 focus:outline-none transition"
            >
              <span className="inline-block w-2 h-2 bg-green-500 rounded-full" />
              <span className="font-medium text-sm">Live</span>
            </button>

            <button
              onClick={() => router.push('/aion/AIONDashboard')}
              className="flex items-center space-x-1 py-1 px-3 border border-blue-500 text-blue-600 rounded-lg bg-white dark:bg-gray-900 text-sm hover:bg-blue-50 dark:hover:bg-gray-700 focus:outline-none transition"
            >
              <Image src="/aion-icon.svg" alt="AION" width={16} height={16} />
              <span className="font-medium">AION</span>
            </button>

            {!account ? (
              <button
                onClick={handleConnect}
                className="py-1 px-3 border border-black rounded-lg bg-transparent text-black dark:text-white text-sm hover:bg-gray-100 dark:hover:bg-gray-700 focus:outline-none transition"
              >
                Connect Wallet
              </button>
            ) : (
              <div ref={wrapperRef} className="relative">
                <button
                  onClick={() => setDropdownOpen(o => !o)}
                  className="py-1 px-3 border border-black rounded-lg bg-transparent text-black dark:text-white text-sm hover:bg-gray-100 dark:hover:bg-gray-700 focus:outline-none transition"
                >
                  {shortAddr}
                </button>
                {dropdownOpen && (
                  <div className="absolute right-0 mt-2 w-40 bg-white dark:bg-gray-800 border border-border-light dark:border-gray-700 rounded-lg shadow-lg z-50">
                    <button
                      onClick={handleDisconnect}
                      className="w-full text-left px-4 py-2 text-text-primary dark:text-text-secondary text-sm hover:bg-gray-100 dark:hover:bg-gray-700 focus:outline-none transition"
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