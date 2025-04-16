// src/lib/withAuth.ts
"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

// 🔐 Higher-Order Component to protect routes
const withAuth = <P extends object>(Component: React.ComponentType<P>) => {
  return function AuthenticatedComponent(props: P) {
    const router = useRouter();

    useEffect(() => {
      const token = localStorage.getItem("token");
      if (!token) {
        router.push("/login"); // Redirect to login if not authenticated
      }
    }, [router]);

    return <Component {...props} />;
  };
};

export default withAuth;

