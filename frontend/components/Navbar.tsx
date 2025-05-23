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

  const handleConnect = useCallback(async () => {
    // clear any previous “do not auto-connect”
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
    // remember that user chose to opt-out of auto-connect
    localStorage.setItem('manualDisconnect', 'true')
    logout()   // clears token + reloads page
    setAccount(null)
    setRole(null)
    setDropdownOpen(false)
    router.push('/')
  }, [router])

  useEffect(() => {
    const eth = (window as any).ethereum
    if (!eth) return

    // 1) if we already have a JWT, fetch + hydrate the role
    const token = localStorage.getItem('token')
    if (token) {
      api.defaults.headers.common.Authorization = `Bearer ${token}`
      api.get('/auth/role')
        .then(res => setRole(res.data.role as UserRole))
        .catch(() => {
          localStorage.removeItem('token')
          delete api.defaults.headers.common.Authorization
        })
    }

    // 2) Only auto-connect if the user hasn't manually disconnected
    const manuallyDisconnected = localStorage.getItem('manualDisconnect') === 'true'
    if (!manuallyDisconnected) {
      eth.request({ method: 'eth_accounts' })
        .then((accounts: string[]) => {
          if (accounts.length) setAccount(accounts[0])
        })
        .catch(console.error)
    }

    // 3) Watch for on-chain account changes and treat them as explicit disconnects
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
  }, [handleDisconnect])

  // close dropdown when clicking outside
  useEffect(() => {
    function onClick(e: MouseEvent) {
      if ( dropdownOpen &&
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

  return (
    <header className="sticky top-0 bg-white border-b z-50">
      <div className="max-w-7xl mx-auto flex h-16 items-center justify-between px-4">
        <Link href="/" className="flex items-center">
          <Image src="/stickey.png" width={144} height={48} alt="Logo" priority />
        </Link>

        {/* only render the role-pill once `role` is set */}
        {role && (
          <span className="text-sm px-2 py-1 bg-gray-100 rounded">
            Role: {role}
          </span>
        )}

        <div className="flex items-center space-x-6">
          <Link href="/" className="text-gray-700 hover:underline">Marketplace</Link>

          {!account && (
            <Link href="/register" className="text-gray-700 hover:underline">
              Register
            </Link>
          )}

          {role === 'supplier' && (
            <Link href="/dashboard" className="text-gray-700 hover:underline">
              Supplier Dashboard
            </Link>
          )}
          {role === 'buyer' && (
            <Link href="/buyer/dashboard" className="text-gray-700 hover:underline">
              Buyer Dashboard
            </Link>
          )}
          {role === 'admin' && (
            <Link href="/admin/dashboard" className="text-gray-700 hover:underline">
              Admin Dashboard
            </Link>
          )}

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
