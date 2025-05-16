// pages/admin/dashboard.tsx

import { useEffect, useState } from 'react'
import Navbar from '@/components/Navbar'
import useAuthRedirect from '@/hooks/useAuthRedirect'
import api from '@/lib/api'

interface User {
  id: number
  name: string
  email: string
  role: string
}

interface AdminProduct {
  id: number
  title: string
  origin_country: string
  category: string
  owner_email: string
}

interface Deal {
  id: number
  product_title: string
  buyer_email: string
  supplier_email: string
  quantity_kg: number
  total_price: number
}

export default function AdminDashboard() {
  // Redirect away if not an admin
  useAuthRedirect('admin')

  const [users, setUsers] = useState<User[]>([])
  const [products, setProducts] = useState<AdminProduct[]>([])
  const [deals, setDeals] = useState<Deal[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchAdminData = async () => {
      try {
        const [usersRes, productsRes, dealsRes] = await Promise.all([
          api.get<User[]>('/admin/users'),
          api.get<AdminProduct[]>('/admin/products'),
          api.get<Deal[]>('/admin/deals'),
        ])
        setUsers(usersRes.data)
        setProducts(productsRes.data)
        setDeals(dealsRes.data)
      } catch (err) {
        console.error('❌ Error fetching admin data:', err)
        setError('Unauthorized or failed to load admin data.')
      }
    }
    fetchAdminData()
  }, [])

  return (
    <div className="min-h-screen bg-gray-100 text-gray-900">
      <Navbar />
      <main className="p-6 max-w-6xl mx-auto space-y-10">

        <h1 className="text-3xl font-bold mb-6 text-center">🛠️ Admin Dashboard</h1>
        {error && <p className="text-red-500 mb-4 text-center">{error}</p>}

        {/* Users Table */}
        <section>
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
                {users.map((u) => (
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
        <section>
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
                {products.map((p) => (
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
                  <th className="text-left p-2">Quantity (kg)</th>
                  <th className="text-left p-2">Total Price</th>
                </tr>
              </thead>
              <tbody>
                {deals.map((d) => (
                  <tr key={d.id} className="border-t">
                    <td className="p-2">{d.product_title}</td>
                    <td className="p-2">{d.buyer_email}</td>
                    <td className="p-2">{d.supplier_email}</td>
                    <td className="p-2">{d.quantity_kg}</td>
                    <td className="p-2">{d.total_price}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

      </main>
    </div>
  )
}

