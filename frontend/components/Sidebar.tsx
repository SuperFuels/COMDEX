// components/Sidebar.tsx
import Link from 'next/link';
import { useRouter } from 'next/router';
import { useEffect, useState } from 'react';

const Sidebar = () => {
  const router = useRouter();
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('token');
      setIsLoggedIn(!!token);
    }
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('token');
    router.push('/login');
  };

  return (
    <aside className="w-64 h-screen bg-gray-800 text-white p-4">
      <h2 className="text-xl font-bold mb-6">COMDEX</h2>
      <ul className="space-y-4">
        <li>
          <Link href="/dashboard" className="hover:underline">
            Dashboard
          </Link>
        </li>
        <li>
          <Link href="/products/new" className="hover:underline">
            Add Product
          </Link>
        </li>
        <li>
          <Link href="/deals" className="hover:underline">
            My Deals
          </Link>
        </li>
        {isLoggedIn && (
          <li>
            <button onClick={handleLogout} className="underline">
              Logout
            </button>
          </li>
        )}
      </ul>
    </aside>
  );
};

export default Sidebar;

