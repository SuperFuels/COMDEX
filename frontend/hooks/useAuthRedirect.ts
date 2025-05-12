// frontend/hooks/useAuthRedirect.ts

import { useEffect } from 'react'
import { useRouter } from 'next/router'
import api from '@/lib/api'

// Define the possible user roles
export type UserRole = 'supplier' | 'buyer' | 'admin'

export default function useAuthRedirect(requiredRole?: UserRole) {
  const router = useRouter()

  useEffect(() => {
    console.log('[useAuthRedirect] 🔍 running for route:', router.pathname)
    const token = localStorage.getItem('token')
    console.log('[useAuthRedirect] token:', token)

    // If there's no token in localStorage, send to login
    if (!token) {
      console.log('[useAuthRedirect] ➡️ no token, redirect to /login')
      router.replace('/login')
      return
    }

    // Validate role with backend
    api.get('/auth/role')
      .then(res => {
        console.log('[useAuthRedirect] /auth/role →', res.status, res.data)
        const userRole = res.data.role as UserRole
        console.log('[useAuthRedirect] userRole:', userRole, 'requiredRole:', requiredRole)

        // If a requiredRole is specified and does not match, redirect
        if (requiredRole && userRole !== requiredRole) {
          console.log(
            `[useAuthRedirect] ➡️ role mismatch (have=${userRole} need=${requiredRole}), redirect to /login`
          )
          router.replace('/login')
        } else {
          console.log('[useAuthRedirect] ✅ role ok, staying on page')
        }
      })
      .catch(err => {
        console.error('[useAuthRedirect] ❌ error fetching role', err)
        router.replace('/login')
      })
  }, [requiredRole, router])
}

