import { useEffect, useState } from 'react';
import axios from 'axios';
import { useRouter } from 'next/router';
import useAuthRedirect from '@/hooks/useAuthRedirect';

export default function AdminDashboard() {
  const router = useRouter();
  const [users, setUsers] = useState([]);
  const [products, setProducts] = useState([]);
  const [deals, setDeals] = useState([]);
  const [error, setError] = useState('');

  useAuthRedirect('admin'); // 🔐 Protect this route (admin only)

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) return;

    const fetchAdminData = async () => {
      try {
        const headers = {
          Authorization: `Bearer ${token}`,
        };

        const [usersRes, productsRes, dealsRes] = await Promise.all([
          axios.get('http://localhost:8000/admin/users', { headers }),
          axios.get('http://localhost:8000/admin/products', { headers }),
          axios.get('http://localhost:8000/admin/deals', { headers }),
        ]);

        setUsers(usersRes.data);
        setProducts(productsRes.data);
        setDeals(dealsRes.data);
      } catch (err: any) {
        console.error(err);
        setError('Unauthorized or failed to load admin data.');
      }
    };

    fetchAdminData();
  }, []);

  return (
    <main className="p-6 bg-gray-100 min-h-screen">
      <h1 className="text-3xl font-bold mb-6 text-center">🛠️ Admin Dashboard</h1>

      {error && <p className="text-red-500 mb-4 text-center">{error}</p>}

      {/* Users Table */}
      <section className="mb-10">
        <h2 className="text-xl font-semibold mb-2">👥 All Users</h2>
        <div className="bg-white shadow p-4 rounded overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr>
                <th className="text-left p-2">Name</th>
                <th className="text-left p-2">Email</th>
                <th className="text-left p-2">Role</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u: any) => (
                <tr key={u.id} className="border-t">
                  <td className="p-2">{u.name}</td>
                  <td className="p-2">{u.email}</td>
                  <td className="p-2 capitalize">{u.role}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Products Table */}
      <section className="mb-10">
        <h2 className="text-xl font-semibold mb-2">📦 All Products</h2>
        <div className="bg-white shadow p-4 rounded overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr>
                <th className="text-left p-2">Title</th>
                <th className="text-left p-2">Country</th>
                <th className="text-left p-2">Category</th>
                <th className="text-left p-2">Owner</th>
              </tr>
            </thead>
            <tbody>
              {products.map((p: any) => (
                <tr key={p.id} className="border-t">
                  <td className="p-2">{p.title}</td>
                  <td className="p-2">{p.origin_country}</td>
                  <td className="p-2">{p.category}</td>
                  <td className="p-2">{p.owner_email}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Deals Table */}
      <section>
        <h2 className="text-xl font-semibold mb-2">🤝 All Deals</h2>
        <div className="bg-white shadow p-4 rounded overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr>
                <th className="text-left p-2">Product</th>
                <th className="text-left p-2">Buyer</th>
                <th className="text-left p-2">Supplier</th>
                <th className="text-left p-2">Qty (kg)</th>
                <th className="text-left p-2">Total $</th>
              </tr>
            </thead>
            <tbody>
              {deals.map((d: any) => (
                <tr key={d.id} className="border-t">
                  <td className="p-2">{d.product_title}</td>
                  <td className="p-2">{d.buyer_email}</td>
                  <td className="p-2">{d.supplier_email}</td>
                  <td className="p-2">{d.quantity_kg}</td>
                  <td className="p-2">${d.total_price}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}

