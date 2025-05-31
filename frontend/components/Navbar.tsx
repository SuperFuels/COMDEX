// frontend/components/Navbar.tsx

import Link from 'next/link'
import Image from 'next/image'
import { useRouter } from 'next/router'
import { useEffect, useState, useRef, useCallback } from 'react'
import api from '@/lib/api'
import { UserRole } from '@/hooks/useAuthRedirect'
import { signInWithEthereum, logout } from '@/utils/auth'
import { DarkModeToggle } from './DarkModeToggle'

export default function Navbar() {
  const router = useRouter()
  const [account, setAccount] = useState<string | null>(null)
  const [role, setRole]       = useState<UserRole | null>(null)
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const wrapperRef = useRef<HTMLDivElement>(null)

  // Connect wallet / SIWE
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

  // Logout
  const handleDisconnect = useCallback(() => {
    localStorage.setItem('manualDisconnect', 'true')
    logout()
    setAccount(null)
    setRole(null)
    setDropdownOpen(false)
    router.push('/')
  }, [router])

  // Hydrate JWT or Wallet on mount
  useEffect(() => {
    // 1) JWT
    if (typeof window !== 'undefined') {
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

  // Close dropdown if clicked outside
  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (
        dropdownOpen &&
        wrapperRef.current &&
        !wrapperRef.current.contains(e.target as Node)
      ) {
        setDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [dropdownOpen])

  const shortAddr = account
    ? `${account.slice(0, 6)}…${account.slice(-4)}`
    : ''

  // Build dashboard path by role
  const dashboardPath =
    role === 'admin'    ? '/admin/dashboard'   :
    role === 'supplier' ? '/supplier/dashboard':
    role === 'buyer'    ? '/buyer/dashboard'    :
    undefined

  // A little helper to trigger the Sidebar’s toggle button
  const openSidebar = () => {
    const btn = document.getElementById('sidebarToggle')
    if (btn) (btn as HTMLButtonElement).click()
  }

  return (
    <header className="sticky top-0 z-50 bg-background-header dark:bg-background-dark border-b border-gray-200 dark:border-gray-700">
      <div className="max-w-7xl mx-auto flex items-center justify-between h-16 px-4">
        {/* Logo */}
        <Link href="/" className="flex items-center">
          <Image
            src="/Stickeyai.svg"
            alt="Stickey.ai Logo"
            width={144}
            height={48}
            priority
          />
        </Link>

        {/* Empty flex‐spacer so that Connect Wallet + menu icon float right */}
        <div className="flex-1" />

        <div className="flex items-center space-x-4">
          {/* If user is logged in, show their abbreviated address */}
          {account && (
            <div ref={wrapperRef} className="relative">
              <button
                onClick={() => setDropdownOpen(o => !o)}
                className="flex items-center space-x-2 border border-gray-300 dark:border-gray-600 bg-gray-100 dark:bg-gray-700 text-text px-3 py-1 rounded-full hover:bg-gray-200 dark:hover:bg-gray-600 transition"
              >
                <span className="text-sm">{shortAddr}</span>
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className={`h-4 w-4 transform ${dropdownOpen ? 'rotate-180' : 'rotate-0'}`}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              {dropdownOpen && (
                <div className="absolute right-0 mt-2 w-48 bg-background-header dark:bg-background-dark border border-gray-200 dark:border-gray-600 rounded shadow-dropdown z-50">
                  <Link href={dashboardPath ?? "/"}>
                    <a className="block px-4 py-2 text-text hover:bg-gray-100 dark:hover:bg-gray-700">
                      {role ? `${role.charAt(0).toUpperCase() + role.slice(1)} Dashboard` : "Dashboard"}
                    </a>
                  </Link>
                  <button
                    onClick={handleDisconnect}
                    className="block w-full text-left px-4 py-2 text-text hover:bg-gray-100 dark:hover:bg-gray-700"
                  >
                    Disconnect
                  </button>
                </div>
              )}
            </div>
          )}

          {/* If no account & no role, show Register/Login as part of dropdown */}
          {!account && !role && (
            <button
              onClick={openSidebar}
              className="text-text hover:text-primary transition text-sm"
            >
              Menu
            </button>
          )}

          {/* Connect Wallet always at far right */}
          <button
            onClick={handleConnect}
            className="btn-primary text-sm"
          >
            Connect Wallet
          </button>

          {/* Hamburger / menu icon to open Sidebar */}
          <button onClick={openSidebar} className="ml-2 p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded">
            <Image src="/g.svg" alt="menu" width={24} height={24} />
          </button>

          {/* Dark Mode Toggle */}
          <DarkModeToggle />
        </div>
      </div>
    </header>
  )
}