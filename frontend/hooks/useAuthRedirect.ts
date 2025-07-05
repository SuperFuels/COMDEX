// File: frontend/hooks/useAuthRedirect.ts

import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import api from "@/lib/api";
import { getToken, logout } from "@/utils/auth";

export type UserRole = "supplier" | "buyer" | "admin";

const PUBLIC_PATHS = ["/login", "/register"];

export default function useAuthRedirect(requiredRole?: UserRole): boolean {
  const router = useRouter();
  const { pathname } = router;
  const [loading, setLoading] = useState(true); // 🟡 Add loading state

  useEffect(() => {
    const token = getToken();

    if (!token) {
      if (!PUBLIC_PATHS.includes(pathname)) {
        router.replace("/login");
      }
      setLoading(false);
      return;
    }

    api.defaults.headers.common.Authorization = `Bearer ${token}`;

    api
      .get<{ role: UserRole }>("/auth/profile")
      .then(({ data }) => {
        const userRole = data.role;

        // ✅ Public page logic
        if (PUBLIC_PATHS.includes(pathname)) {
          switch (userRole) {
            case "supplier":
              return router.replace("/supplier/dashboard");
            case "buyer":
              return router.replace("/buyer/dashboard");
            case "admin":
              return router.replace("/admin/dashboard");
            default:
              return router.replace("/login");
          }
        }

        // ❌ Unauthorized role
        if (requiredRole && userRole !== requiredRole) {
          console.warn(`Access denied: ${userRole} trying to access ${pathname}`);
          return router.replace("/login");
        }

        // ✅ Authorized, let render continue
      })
      .catch((err) => {
        console.error("[useAuthRedirect] token invalid or expired", err);
        logout();
        router.replace("/login");
      })
      .finally(() => setLoading(false)); // ✅ Now safe to render
  }, [pathname, requiredRole, router]);

  return loading; // ⏳ Let caller know when check is still running
}