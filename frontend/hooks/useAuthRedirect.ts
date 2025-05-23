// frontend/hooks/useAuthRedirect.ts
import { useEffect } from 'react'
import { useRouter } from 'next/router'
import api from '@/lib/api'

// our roles
export type UserRole = 'supplier' | 'buyer' | 'admin'

// publicly‐accessible routes
const PUBLIC_PATHS = ['/login', '/register']

export default function useAuthRedirect(requiredRole?: UserRole) {
  const router = useRouter()
  const { pathname } = router

  useEffect(() => {
    const token = localStorage.getItem('token')
    const manualDisconnect = localStorage.getItem('manualDisconnect')

    // 1) If no token (or they've manually disconnected), 
    //    and this isn't a public page, send to /login
    if (!token || manualDisconnect) {
      if (!PUBLIC_PATHS.includes(pathname)) {
        router.replace('/login')
      }
      return
    }

    // 2) We have a token: set it on our axios client
    api.defaults.headers.common.Authorization = `Bearer ${token}`

    // 3) Fetch the actual role from the server
    api.get<{ role: UserRole }>('/auth/role')
      .then(({ data }) => {
        const userRole = data.role

        // 3a) If we're on a public page (login/register), 
        //     send them to their dashboard immediately
        if (PUBLIC_PATHS.includes(pathname)) {
          switch (userRole) {
            case 'supplier':
              return router.replace('/dashboard')
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
      .catch(err => {
        console.error('[useAuthRedirect] error validating token/role', err)
        // Invalid token → clear & force to login
        localStorage.removeItem('token')
        localStorage.removeItem('role')
        router.replace('/login')
      })
  }, [pathname, requiredRole, router])
}
