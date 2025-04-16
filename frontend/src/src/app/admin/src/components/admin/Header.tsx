// src/components/admin/Header.tsx
import React from "react";

const Header = () => {
  return (
    <header className="bg-gray-900 text-white p-4">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Admin Panel</h1>
        <button className="bg-red-600 px-4 py-2 rounded">Logout</button>
      </div>
    </header>
  );
};

export default Header;

