// pages/products/index.tsx
import Sidebar from '@/components/Sidebar';

export default function ProductList() {
  return (
    <div className="flex">
      <Sidebar />
      <div className="p-8 w-full">
        <h1 className="text-2xl font-bold mb-4">My Products</h1>
        <p>Product listing will appear here.</p>
      </div>
    </div>
  );
}

