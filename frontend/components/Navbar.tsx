// frontend/components/Navbar.tsx

import Link from 'next/link'
import Image from 'next/image'
import { useRouter } from 'next/router'
import { useEffect, useState } from 'react'
import axios from 'axios'
import styles from './Header.module.css'

export default function Navbar() {
  const router = useRouter()
  const [search, setSearch]             = useState('')
  const [isLoggedIn, setIsLoggedIn]     = useState(false)
  const [role, setRole]                 = useState<string>('')
  const [walletAddress, setWalletAddress] = useState<string | null>(null)

  // Check JWT + fetch role
  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem('token')
      if (!token) { setIsLoggedIn(false); return }
      try {
        const res = await axios.get(
          'http://localhost:8000/auth/role',
          { headers: { Authorization: `Bearer ${token}` } }
        )
        setIsLoggedIn(true)
        setRole(res.data.role)
      } catch {
        setIsLoggedIn(false)
        setRole('')
      }
    }
    checkAuth()
    router.events.on('routeChangeComplete', checkAuth)
    return () => router.events.off('routeChangeComplete', checkAuth)
  }, [router])

  // MetaMask connect
  useEffect(() => {
    if ((window as any).ethereum) {
      ;(window as any).ethereum
        .request({ method: 'eth_requestAccounts' })
        .then((accounts: string[]) => setWalletAddress(accounts[0]))
        .catch(console.error)
    }
  }, [])

  const handleLogout = () => {
    localStorage.removeItem('token')
    setIsLoggedIn(false)
    setRole('')
    router.push('/login')
  }

  const submitSearch = (e: React.FormEvent) => {
    e.preventDefault()
    const q = search.trim()
    if (q) router.push(`/search?query=${encodeURIComponent(q)}`)
  }

  return (
    <nav className={styles.navbar}>
      <div className={styles.left}>
        <Link href="/">
          <Image
            src="/stickey.png"
            alt="Stickey Logo"
            width={144}
            height={48}
            className={styles.logoImage}
          />
        </Link>
      </div>

      <form onSubmit={submitSearch} className={styles.searchForm}>
        <input
          className={styles.searchInput}
          type="text"
          placeholder="Search commodities..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <button type="submit" className={styles.searchButton}>
          Search
        </button>
      </form>

      <div className={styles.right}>
        {!isLoggedIn ? (
          <>
            <Link href="/login" className={styles.link}>
              Login
            </Link>
            <Link href="/register/seller" className={styles.link}>
              Sellers
            </Link>
            <Link href="/register/buyer" className={styles.link}>
              Buyers
            </Link>
          </>
        ) : (
          <>
            {role === 'admin' && (
              <Link href="/admin/dashboard" className={styles.link}>
                Admin Panel
              </Link>
            )}
            {role === 'supplier' && (
              <>
                <Link href="/dashboard" className={styles.link}>
                  Dashboard
                </Link>
                <Link href="/products/create" className={styles.link}>
                  New Product
                </Link>
              </>
            )}
            {role === 'buyer' && (
              <>
                <Link href="/" className={styles.link}>
                  Marketplace
                </Link>
                <Link href="/deals" className={styles.link}>
                  My Deals
                </Link>
                <Link href="/dashboard" className={styles.link}>
                  Dashboard
                </Link>
              </>
            )}
            <button onClick={handleLogout} className={styles.link}>
              Logout
            </button>
          </>
        )}

        {walletAddress ? (
          <span className={styles.walletAddress}>
            {walletAddress.slice(0, 6)}…{walletAddress.slice(-4)}
          </span>
        ) : (
          <button
            onClick={() =>
              (window as any).ethereum.request({ method: 'eth_requestAccounts' })
            }
            className={styles.connectButton}
          >
            Connect Wallet
          </button>
        )}
      </div>
    </nav>
  )
}

