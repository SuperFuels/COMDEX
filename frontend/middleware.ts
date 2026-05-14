// frontend/middleware.ts
import { NextResponse, NextRequest } from "next/server";

export const config = {
  matcher: [
    // guard /contracts/:id except literal 'new'
    "/contracts/:id((?!new$).*)",
    // sample/zoom endpoints under products
    "/products/:path*/sample",
    "/products/:path*/zoom",
  ],
};

export function middleware(req: NextRequest) {
  const token = req.cookies.get("token")?.value;
  if (!token) {
    const loginUrl = req.nextUrl.clone();
    loginUrl.pathname = "/login";
    return NextResponse.redirect(loginUrl);
  }
  return NextResponse.next();
}