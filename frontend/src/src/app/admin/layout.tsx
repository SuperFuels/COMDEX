// src/app/admin/layout.tsx
import React from "react";
import Sidebar from "@/components/admin/Sidebar";
import Header from "@/components/admin/Header";
import { withAuth } from "@/lib/withAuth"; // Ensure admin route protection

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex">
      <Sidebar />
      <div className="flex-1">
        <Header />
        <div className="p-6">{children}</div>
      </div>
    </div>
  );
}

export const AdminProtectedLayout = withAuth(AdminLayout); // Protect all admin routes

