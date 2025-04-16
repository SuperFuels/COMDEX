// src/components/admin/Sidebar.tsx
import React from "react";
import Link from "next/link";

const Sidebar = () => {
  return (
    <div className="w-64 bg-gray-800 text-white min-h-screen p-4">
      <h1 className="text-xl font-semibold mb-6">Admin Panel</h1>
      <ul>
        <li className="mb-4">
          <Link href="/admin/dashboard">Dashboard</Link>
        </li>
        <li className="mb-4">
          <Link href="/admin/products">Products</Link>
        </li>
        <li className="mb-4">
          <Link href="/admin/orders">Orders</Link>
        </li>
        <li className="mb-4">
          <Link href="/admin/users">Users</Link>
        </li>
      </ul>
    </div>
  );
};

export default Sidebar;

