// hooks/useAuthRedirect.ts
import { useEffect } from 'react';
import { useRouter } from 'next/router';
import axios from 'axios';

export default function useAuthRedirect(requiredRole?: 'admin' | 'supplier' | 'buyer') {
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      router.push('/login');
      return;
    }

    const validate = async () => {
      try {
        const res = await axios.get('http://localhost:8000/auth/role', {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        const userRole = res.data.role;

        if (requiredRole && userRole !== requiredRole) {
          // Redirect to correct dashboard if not allowed
          if (userRole === 'admin') {
            router.push('/admin/dashboard');
          } else if (userRole === 'supplier') {
            router.push('/dashboard'); // Supplier dashboard
          } else {
            router.push('/buyer/dashboard'); // Buyer fallback
          }
        }
      } catch (err) {
        console.error('⚠️ Token validation failed:', err);
        router.push('/login');
      }
    };

    validate();
  }, [router, requiredRole]);
}

