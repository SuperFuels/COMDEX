"use client"

import { useEffect, useState } from 'react'
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

export async function getServerSideProps() {
  return { props: {} };
}

export default function AdminDashboard() {
  // 1) Enforce login + admin
  useAuthRedirect('admin')

  // 2) Local state
  const [users, setUsers]       = useState<User[] | null>(null)
  const [products, setProducts] = useState<AdminProduct[] | null>(null)
  const [deals, setDeals]       = useState<Deal[] | null>(null)
  const [error, setError]       = useState<string | null>(null)

  // 3) Fetch once
  useEffect(() => {
    async function load() {
      try {
        const [u, p, d] = await Promise.all([
          api.get<User[]>('/admin/users'),
          api.get<AdminProduct[]>('/admin/products'),
          api.get<Deal[]>('/admin/deals'),
        ])
        setUsers(u.data)
        setProducts(p.data)
        setDeals(d.data)
      } catch (e) {
        console.error('❌ Error fetching admin data:', e)
        setError('Unauthorized or failed to load admin data.')
      }
    }
    load()
  }, [])

  // 4) Loading state
  if (!users || !products || !deals) {
    return (
      <main className="pt-6 px-6 pb-6 max-w-4xl mx-auto text-center">
        {error
          ? <p className="text-red-500">{error}</p>
          : <p>Loading admin dashboard…</p>
        }
      </main>
    )
  }

  return (
    <main className="pt-6 px-6 pb-6 max-w-6xl mx-auto space-y-10">
      <h1 className="text-3xl font-bold mb-6 text-center">🛠️ Admin Dashboard</h1>

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
              {users.map(u => (
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
              {products.map(p => (
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
              {deals.map(d => (
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
  )
}