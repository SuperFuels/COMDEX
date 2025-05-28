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
  const [role, setRole]       = useState<UserRole | null>(null)
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const wrapperRef = useRef<HTMLDivElement>(null)

  // SIWE-login via wallet
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

  // Manual logout
  const handleDisconnect = useCallback(() => {
    localStorage.setItem('manualDisconnect', 'true')
    logout()
    setAccount(null)
    setRole(null)
    setDropdownOpen(false)
    router.push('/')
  }, [router])

  // Hydrate email/password JWT and/or wallet
  useEffect(() => {
    const eth = (window as any).ethereum

    // 1) JWT login
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
    if (eth) {
      const manuallyDisconnected = localStorage.getItem('manualDisconnect') === 'true'
      if (!manuallyDisconnected) {
        eth.request({ method: 'eth_accounts' })
           .then((accounts: string[]) => accounts[0] && setAccount(accounts[0]))
           .catch(console.error)
      }

      // 3) handle wallet changes
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

  // close dropdown on outside click
  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (dropdownOpen && wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [dropdownOpen])

  const shortAddr = account
    ? `${account.slice(0, 6)}…${account.slice(-4)}`
    : ''

  // determine /<role>/dashboard path
  const dashboardPath = role === 'admin'
    ? '/admin/dashboard'
    : role === 'supplier'
      ? '/supplier/dashboard'
      : role === 'buyer'
        ? '/buyer/dashboard'
        : undefined

  return (
    <header className="sticky top-0 bg-white border-b z-50">
      <div className="max-w-7xl mx-auto flex h-16 items-center justify-between px-4">
        {/* Logo */}
        <Link href="/" className="flex items-center">
          <Image src="/stickey.png" width={144} height={48} alt="Logo" priority />
        </Link>

        <div className="flex items-center space-x-6">
          <Link href="/" className="text-gray-700 hover:underline">
            Marketplace
          </Link>

          {/* Unauthenticated */}
          {!account && !role && (
            <>
              <Link href="/register" className="text-gray-700 hover:underline">
                Register
              </Link>
              <Link href="/login" className="text-gray-700 hover:underline">
                Login
              </Link>
            </>
          )}

          {/* Role‐based dashboard link */}
          {dashboardPath && (
            <Link href={dashboardPath} className="text-gray-700 hover:underline">
              {role!.charAt(0).toUpperCase() + role!.slice(1)} Dashboard
            </Link>
          )}

          {/* Wallet connect / account menu */}
          {!account ? (
            <button
              onClick={handleConnect}
              className="bg-blue-600 text-white px-3 py-1 rounded"
            >
              Connect Wallet
            </button>
          ) : (
            <div ref={wrapperRef} className="relative">
              <button
                onClick={() => setDropdownOpen(o => !o)}
                className="bg-gray-100 px-3 py-1 rounded-full border border-gray-300"
              >
                {shortAddr}
              </button>
              {dropdownOpen && (
                <div className="absolute right-0 mt-2 w-40 bg-white border rounded shadow">
                  <button
                    onClick={handleDisconnect}
                    className="w-full text-left px-4 py-2 hover:bg-gray-100"
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
  )
}