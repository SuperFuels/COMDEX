import { useEffect } from "react";
import { useRouter } from "next/router";
import axios from "axios";

export function useRoleGuard(allowedRoles: string[]) {
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem("token");

    if (!token) {
      router.push("/"); // Not logged in
      return;
    }

    axios
      .get("http://localhost:8000/auth/role", {
        headers: { Authorization: `Bearer ${token}` },
      })
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

