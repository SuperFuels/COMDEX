// middleware.ts
import { NextResponse, NextRequest } from 'next/server'

export const config = {
  matcher: [
    // guard all contracts/:id EXCEPT “new”
    '/contracts/:id((?!new).*)',
    '/dashboard/:path*',
    '/products/:path*/sample',
    '/products/:path*/zoom',
  ],
}

export function middleware(req: NextRequest) {
  const token = req.cookies.get('token')
  if (!token) {
    return NextResponse.redirect(new URL('/login', req.url))
  }
  return NextResponse.next()
}

