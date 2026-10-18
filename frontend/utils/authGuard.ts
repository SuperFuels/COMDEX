"use client"

import { useEffect } from "react";
import { useRouter } from "next/router";
import api from "@/lib/api";

export function useRoleGuard(allowedRoles: string[]) {
  const router = useRouter();

  useEffect(() => {
    api
      .get("/auth/profile", { withCredentials: true })
      .then((res) => {
        const userRole = res.data.role;
        if (!allowedRoles.includes(userRole)) {
          router.push("/"); // Logged in, but not authorized
        }
      })
      .catch(() => {
        router.push("/"); // Token invalid or expired
      });
  }, [allowedRoles, router]);
}
