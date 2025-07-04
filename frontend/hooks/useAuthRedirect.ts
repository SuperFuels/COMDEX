// File: frontend/hooks/useAuthRedirect.ts

import { useEffect } from 'react'
import { useRouter } from 'next/router'
import api from '@/lib/api'
import { getToken, logout } from '@/utils/auth'

export type UserRole = 'supplier' | 'buyer' | 'admin'

const PUBLIC_PATHS = ['/login', '/register']

export default function useAuthRedirect(requiredRole?: UserRole) {
  const router = useRouter()
  const { pathname } = router

  useEffect(() => {
    const token = getToken()

    // 1) No token + not on a public route → redirect to login
    if (!token) {
      if (!PUBLIC_PATHS.includes(pathname)) {
        router.replace('/login')
      }
      return
    }

    // 2) Set token on API for authenticated requests
    api.defaults.headers.common.Authorization = `Bearer ${token}`

    // 3) Validate token by hitting profile endpoint
    api
      .get<{ role: UserRole }>('/auth/profile')
      .then(({ data }) => {
        const userRole = data.role

        // 3a) On public pages (login/register), redirect to appropriate dashboard
        if (PUBLIC_PATHS.includes(pathname)) {
          switch (userRole) {
            case 'supplier':
              return router.replace('/supplier/dashboard')
            case 'buyer':
              return router.replace('/buyer/dashboard')
            case 'admin':
              return router.replace('/admin/dashboard')
            default:
              return router.replace('/login')
          }
        }

        // 3b) Enforce required role if provided
        if (requiredRole && userRole !== requiredRole) {
          console.warn(`Access denied: ${userRole} trying to access ${pathname}`)
          return router.replace('/login')
        }

        // ✅ Otherwise: role is allowed, stay on page
      })
      .catch((err) => {
        console.error('[useAuthRedirect] token invalid or expired', err)
        logout()
        router.replace('/login')
      })
  }, [pathname, requiredRole, router])
}