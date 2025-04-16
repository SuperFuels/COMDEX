'use client';

import { ReactNode } from 'react';
import Header from '@/components/Header';

interface AdminLayoutProps {
  children: ReactNode;
}

const AdminLayout = ({ children }: AdminLayoutProps) => {
  return (
    <div className="bg-gray-100 min-h-screen">
      <Header />
      <main className="p-6">{children}</main>
    </div>
  );
};

export default AdminLayout;

