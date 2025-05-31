// frontend/components/Navbar.tsx
import Link from 'next/link'
import Image from 'next/image'
import { useRouter } from 'next/router'
import { useEffect, useState, useRef, useCallback } from 'react'
import api from '@/lib/api'
import { UserRole } from '@/hooks/useAuthRedirect'
import { signInWithEthereum, logout } from '@/utils/auth'

export default function Navbar() {
  const router = useRouter()
  const [account, setAccount] = useState<string | null>(null)
  const [role, setRole] = useState<UserRole | null>(null)
  const [dropdownOpen, setDropdownOpen] = useState(false)
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
      if (err.response?.status === 404) {
        router.push('/register')
      }
    }
  }, [router])

  // 2) Manual logout
  const handleDisconnect = useCallback(() => {
    localStorage.setItem('manualDisconnect', 'true')
    logout()
    setAccount(null)
    setRole(null)
    setDropdownOpen(false)
    router.push('/')
  }, [router])

  // 3) Hydrate JWT and/or wallet on mount
  useEffect(() => {
    // JWT‐based login
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null
    if (token) {
      api.defaults.headers.common.Authorization = `Bearer ${token}`
      api
        .get<{ role: UserRole }>('/auth/profile')
        .then(res => {
          setRole(res.data.role)
        })
        .catch(() => {
          localStorage.removeItem('token')
          delete api.defaults.headers.common.Authorization
        })
    }

    // Wallet auto‐reconnect
    const eth = (window as any)?.ethereum
    if (eth) {
      const manuallyDisconnected = localStorage.getItem('manualDisconnect') === 'true'
      if (!manuallyDisconnected) {
        eth
          .request({ method: 'eth_accounts' })
          .then((accounts: string[]) => {
            if (accounts[0]) {
              setAccount(accounts[0])
            }
          })
          .catch(console.error)
      }

      // Listen for account changes
      const onAccountsChanged = (accounts: string[]) => {
        if (accounts.length === 0) {
          handleDisconnect()
        } else if (!manuallyDisconnected) {
          setAccount(accounts[0])
        }
      }
      eth.on('accountsChanged', onAccountsChanged)
      return () => void eth.removeListener('accountsChanged', onAccountsChanged)
    }
  }, [handleDisconnect])

  // 4) Close dropdown if clicked outside
  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (dropdownOpen && wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', onClickOutside)
    return () => void document.removeEventListener('mousedown', onClickOutside)
  }, [dropdownOpen])

  const shortAddr = account ? `${account.slice(0, 6)}…${account.slice(-4)}` : ''

  // Decide where “Dashboard” should point
  const dashboardPath =
    role === 'admin'
      ? '/admin/dashboard'
      : role === 'supplier'
      ? '/supplier/dashboard'
      : role === 'buyer'
      ? '/buyer/dashboard'
      : undefined

  return (
    <header className="sticky top-0 bg-background-header dark:bg-background-dark border-b z-50">
      <div className="max-w-7xl mx-auto flex items-center h-16 px-4">
        {/* Logo on the far left */}
        <Link href="/" className="flex items-center">
          <Image
            src="/stickeyai.svg"
            alt="Stickey.ai Logo"
            width={144}
            height={48}
            priority
          />
        </Link>

        {/* Dropdown toggler: “G.svg” icon */}
        <div ref={wrapperRef} className="relative ml-6">
          <button
            onClick={() => setDropdownOpen(o => !o)}
            className="p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-700 transition"
          >
            <Image src="/g.svg" alt="Menu" width={24} height={24} />
          </button>

          {dropdownOpen && (
            <ul className="absolute left-0 mt-2 w-48 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded shadow-dropdown">
              {/* Always show “Marketplace” */}
              <li>
                <Link href="/" className="block px-4 py-2 text-text hover:bg-gray-100 dark:hover:bg-gray-700 transition">
                  Marketplace
                </Link>
              </li>

              {/* If not logged in at all, show Register & Login */}
              {!account && !role && (
                <>
                  <li>
                    <Link href="/register" className="block px-4 py-2 text-text hover:bg-gray-100 dark:hover:bg-gray-700 transition">
                      Register
                    </Link>
                  </li>
                  <li>
                    <Link href="/login" className="block px-4 py-2 text-text hover:bg-gray-100 dark:hover:bg-gray-700 transition">
                      Login
                    </Link>
                  </li>
                </>
              )}

              {/* If we have a dashboardPath (i.e. user is logged‐in), show Dashboard link */}
              {dashboardPath && (
                <li>
                  <Link href={dashboardPath} className="block px-4 py-2 text-text hover:bg-gray-100 dark:hover:bg-gray-700 transition">
                    {role![0].toUpperCase() + role!.slice(1)} Dashboard
                  </Link>
                </li>
              )}
            </ul>
          )}
        </div>

        {/* Spacer → push Connect Wallet all the way right */}
        <div className="flex-1" />

        {/* Connect Wallet or Account Dropdown on the far right */}
        {!account ? (
          <button
            onClick={handleConnect}
            className="bg-primary hover:bg-primaryHover text-white px-3 py-1 rounded transition"
          >
            Connect Wallet
          </button>
        ) : (
          <div ref={wrapperRef} className="relative">
            <button
              onClick={() => setDropdownOpen(o => !o)}
              className="bg-gray-200 dark:bg-gray-700 text-text px-3 py-1 rounded-full border border-gray-300 dark:border-gray-600 hover:bg-gray-300 dark:hover:bg-gray-600 transition"
            >
              {shortAddr}
            </button>

            {/* If account is clicked, show “Disconnect” */}
            {dropdownOpen && (
              <div className="absolute right-0 mt-2 w-40 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded shadow-dropdown">
                <button
                  onClick={handleDisconnect}
                  className="w-full text-left px-4 py-2 text-text hover:bg-gray-100 dark:hover:bg-gray-700 transition"
                >
                  Disconnect
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </header>
  )
}