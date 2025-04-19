import React from 'react';
import Link from 'next/link';

export default function Home() {
  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-5xl font-bold mb-4">Welcome to COMDEX</h1>
        <p className="text-lg mb-6">The next-gen commodity trading platform.</p>
        <div className="flex justify-center space-x-4">
          <Link href="/login" className="bg-blue-600 text-white px-4 py-2 rounded">
            Login
          </Link>
          <Link href="/register" className="bg-gray-800 text-white px-4 py-2 rounded">
            Register
          </Link>
        </div>
      </div>
    </div>
  );
}

