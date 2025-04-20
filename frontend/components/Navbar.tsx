import Link from 'next/link';
import { useRouter } from 'next/router';
import { useEffect, useState } from 'react';
import axios from 'axios';

const Navbar = () => {
  const router = useRouter();
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [role, setRole] = useState('');

  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem('token');
      if (!token) return;

      try {
        const res = await axios.get('http://localhost:8000/auth/role', {
          headers: { Authorization: `Bearer ${token}` },
        });
        setIsLoggedIn(true);
        setRole(res.data.role);
      } catch {
        setIsLoggedIn(false);
        setRole('');
      }
    };

    checkAuth();
    router.events?.on('routeChangeComplete', checkAuth);
    return () => {
      router.events?.off('routeChangeComplete', checkAuth);
    };
  }, [router]);

  const handleLogout = () => {
    localStorage.removeItem('token');
    setIsLoggedIn(false);
    setRole('');
    router.push('/login');
  };

  return (
    <nav className="w-full bg-black text-white px-6 py-4 flex justify-between items-center">
      <Link href="/" className="text-xl font-bold text-pink-500">
        COMDEX
      </Link>

      <div className="space-x-6 text-sm">
        {isLoggedIn ? (
          <>
            {role === 'admin' && (
              <Link href="/admin/dashboard" className="hover:text-pink-400 transition">
                Admin Panel
              </Link>
            )}
            {role === 'supplier' && (
              <>
                <Link href="/supplier/dashboard" className="hover:text-pink-400 transition">
                  Supplier Dashboard
                </Link>
                <Link href="/products/new" className="hover:text-pink-400 transition">
                  + New Product
                </Link>
              </>
            )}
            {role === 'buyer' && (
              <Link href="/dashboard" className="hover:text-pink-400 transition">
                Buyer Dashboard
              </Link>
            )}

            <Link href="/deals" className="hover:text-pink-400 transition">
              My Deals
            </Link>
            <button
              onClick={handleLogout}
              className="hover:text-red-400 transition ml-2"
            >
              Logout
            </button>
          </>
        ) : (
          <>
            <Link href="/login" className="hover:text-pink-400 transition">
              Login
            </Link>
            <Link href="/register" className="hover:text-pink-400 transition">
              Register
            </Link>
          </>
        )}
      </div>
    </nav>
  );
};

export default Navbar;

