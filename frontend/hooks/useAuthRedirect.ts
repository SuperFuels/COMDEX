// frontend/hooks/useAuthRedirect.ts

import { useEffect } from 'react'
import { useRouter } from 'next/router'
import api from '@/lib/api'
import { getToken, logout } from '@/utils/auth'

// our roles
export type UserRole = 'supplier' | 'buyer' | 'admin'

// publicly‐accessible routes
const PUBLIC_PATHS = ['/login', '/register']

export default function useAuthRedirect(requiredRole?: UserRole) {
  const router = useRouter()
  const { pathname } = router

  useEffect(() => {
    const token = getToken()

    // 1) If no token, and this isn’t a public page, send to /login
    if (!token) {
      if (!PUBLIC_PATHS.includes(pathname)) {
        router.replace('/login')
      }
      return
    }

    // 2) We have a token: set it on axios
    api.defaults.headers.common.Authorization = `Bearer ${token}`

    // 3) Fetch the actual role from the server
    api
      .get<{ role: UserRole }>('/auth/profile')
      .then(({ data }) => {
        const userRole = data.role

        // 3a) If we’re on a public page (login/register),
        //     send them to their dashboard immediately
        if (PUBLIC_PATHS.includes(pathname)) {
          switch (userRole) {
            case 'supplier':
              return router.replace('/supplier/dashboard')
            case 'buyer':
              return router.replace('/buyer/dashboard')
            case 'admin':
              return router.replace('/admin/dashboard')
          }
        }

        // 3b) If this page requires a role, enforce it
        if (requiredRole && userRole !== requiredRole) {
          return router.replace('/login')
        }

        // Otherwise: allowed, stay put
      })
      .catch((err) => {
        console.error('[useAuthRedirect] token validation failed', err)
        // Invalid token → clear & force to login
        logout()
        router.replace('/login')
      })
  }, [pathname, requiredRole, router])
}