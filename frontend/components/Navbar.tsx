// frontend/components/Navbar.tsx

import Link from 'next/link';
import Image from 'next/image';
import { useRouter } from 'next/router';
import { useEffect, useState, useRef, useCallback } from 'react';
import api from '@/lib/api';
import { UserRole } from '@/hooks/useAuthRedirect';

export default function Navbar() {
  const router = useRouter();
  const [account, setAccount] = useState<string | null>(null);
  const [role, setRole] = useState<UserRole | null>(null);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);

  const doLogin = useCallback(
    async (address: string) => {
      try {
        console.log('[SIWE] request nonce for', address);
        const { data: { message } } = await api.get('/auth/nonce', { params: { address } });
        console.log('[SIWE] got message:', message);

        console.log('[SIWE] calling personal_sign…');
        const signature = await (window as any).ethereum.request({
          method: 'personal_sign',
          params: [message, address],
        });
        console.log('[SIWE] signature:', signature);

        console.log('[SIWE] calling /auth/verify…');
        const { data: { token, role: newRole } } =
          await api.post('/auth/verify', { message, signature });
        console.log('[SIWE] verify response:', { token, newRole });

        localStorage.setItem('token', token);
        api.defaults.headers.common.Authorization = `Bearer ${token}`;
        setRole(newRole as UserRole);
      } catch (err: any) {
        console.error('[SIWE] login failed:', err);
        if (err.response?.status === 404) {
          router.push('/register');
          return;
        }
        localStorage.removeItem('token');
        delete api.defaults.headers.common.Authorization;
        setRole(null);
      }
    },
    [router]
  );

  const handleDisconnect = useCallback(() => {
    localStorage.removeItem('token');
    localStorage.setItem('manuallyDisconnected', '1');
    delete api.defaults.headers.common.Authorization;
    setAccount(null);
    setRole(null);
    setDropdownOpen(false);
    router.push('/');
  }, [router]);

  const handleConnect = async () => {
    console.log('[handleConnect] clicked');
    localStorage.removeItem('manuallyDisconnected');
    if (!(window as any).ethereum) {
      return alert('Please install MetaMask');
    }
    try {
      const [addr] = await (window as any).ethereum.request({ method: 'eth_requestAccounts' });
      console.log('[handleConnect] got address', addr);
      setAccount(addr);
      await doLogin(addr);
    } catch (e) {
      console.error('[handleConnect] error:', e);
    }
  };

  // Treat any account switch as a full disconnect
  const handleAccountsChanged = useCallback(
    (accounts: string[]) => {
      console.log('[MetaMask] accountsChanged → disconnecting', accounts);
      handleDisconnect();
    },
    [handleDisconnect]
  );

  useEffect(() => {
    const eth = (window as any).ethereum;
    if (!eth) return;

    const token = localStorage.getItem('token');
    const manually = localStorage.getItem('manuallyDisconnected');

    // If we have a JWT, fetch and set role
    if (token) {
      console.log('[hydrate] existing token → fetch /auth/role');
      api.defaults.headers.common.Authorization = `Bearer ${token}`;
      api.get('/auth/role')
         .then(res => {
           console.log('[hydrate] /auth/role:', res.data);
           setRole(res.data.role as UserRole);
         })
         .catch(err => {
           console.error('[hydrate] /auth/role failed:', err);
           localStorage.removeItem('token');
           delete api.defaults.headers.common.Authorization;
           setRole(null);
         });
    }

    // Just populate current account in UI — no SIWE here
    eth.request({ method: 'eth_accounts' })
      .then((accounts: string[]) => {
        if (manually) {
          console.log('[hydrate] manuallyDisconnected → skip setting account');
          setAccount(null);
          return;
        }
        console.log('[hydrate] current eth_accounts:', accounts);
        setAccount(accounts[0] || null);
      })
      .catch(console.error);

    eth.on('accountsChanged', handleAccountsChanged);
    return () => {
      eth.removeListener('accountsChanged', handleAccountsChanged);
    };
  }, [handleAccountsChanged]);

  // Close dropdown on outside click
  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (dropdownOpen &&
          wrapperRef.current &&
          !wrapperRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, [dropdownOpen]);

  const shortAddr = account ? `${account.slice(0, 6)}…${account.slice(-4)}` : '';

  return (
    <header className="sticky top-0 bg-white border-b z-50">
      <div className="max-w-7xl mx-auto flex h-16 items-center justify-between px-4">
        <Link href="/" className="flex items-center">
          <Image src="/stickey.png" width={144} height={48} alt="Logo" priority />
        </Link>

        {/* Debug badge */}
        <span className="text-sm px-2 py-1 bg-gray-100 rounded">
          Role: {role ?? '⏳null'}
        </span>

        <div className="flex items-center space-x-6">
          <Link href="/" className="text-gray-700 hover:underline">
            Marketplace
          </Link>

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
  );
}
