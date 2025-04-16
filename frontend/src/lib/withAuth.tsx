"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

// 🔐 Higher-Order Component to protect routes
export default function withAuth<P>(Component: React.ComponentType<P>) {
  return function AuthenticatedComponent(props: P) {
    const router = useRouter();

    useEffect(() => {
      const token = localStorage.getItem("token");
      if (!token) {
        router.push("/login");
      }
    }, [router]);

    return <Component {...props} />;
  };
}

