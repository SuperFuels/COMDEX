// middleware.ts2
import { NextResponse, NextRequest } from 'next/server'

export const config = {
  matcher: [
    // guard all contracts/:id EXCEPT “new”
    '/contracts/:id((?!new).*)',
    // sample/zoom endpoints under products
    '/products/:path*/sample',
    '/products/:path*/zoom',
  ],
}

export function middleware(req: NextRequest) {
  // read HTTP-only cookie named "token"
  const token = req.cookies.get('token')?.value

  // if no token, redirect to /login
  if (!token) {
    const loginUrl = req.nextUrl.clone()
    loginUrl.pathname = '/login'
    return NextResponse.redirect(loginUrl)
  }

  return NextResponse.next()
}

