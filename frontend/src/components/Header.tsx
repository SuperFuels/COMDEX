// src/components/Header.tsx

"use client";

import Link from 'next/link';

export default function Header() {
  return (
    <header className="bg-black text-white p-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">
          <span role="img" aria-label="test tube">
            🧪
          </span>{" "}
          COMDEX
        </h1>
        <div className="flex gap-6">
          <Link href="/" className="text-white hover:text-gray-400">Home</Link>
          <Link href="/dashboard" className="text-white hover:text-gray-400">Dashboard</Link>
          <Link href="/create" className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded">Create Product</Link>
          <Link href="/login" className="text-white hover:text-gray-400">Login</Link>
        </div>
      </div>
    </header>
  );
}

