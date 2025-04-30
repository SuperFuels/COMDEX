import { useEffect } from 'react';
import { useRouter } from 'next/router';
import axios from 'axios';

type UserRole = 'admin' | 'supplier' | 'buyer';

export default function useAuthRedirect(requiredRole?: UserRole) {
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

        const userRole: UserRole = res.data.role;

        if (requiredRole && userRole !== requiredRole) {
          // Redirect user to their appropriate dashboard if role mismatch
          if (userRole === 'admin') {
            router.push('/admin/dashboard');
          } else if (userRole === 'supplier') {
            router.push('/dashboard');
          } else {
            router.push('/buyer/dashboard');
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

