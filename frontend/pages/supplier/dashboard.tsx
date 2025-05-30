import Link from 'next/link'
import useAuthRedirect from '@/hooks/useAuthRedirect'
import { useSupplierDashboard } from '@/hooks/useSupplierDashboard'

export default function SupplierDashboard() {
  useAuthRedirect('supplier')
  const { products, metrics, loading, error } = useSupplierDashboard()

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <p className="text-gray-600">Loading dashboard…</p>
    </div>
  )
  if (error) return (
    <div className="min-h-screen flex items-center justify-center">
      <p className="text-red-600">{error}</p>
    </div>
  )

  const cards = [
    { title: "Today's sales", value: `£${metrics.totalSalesToday}` },
    { title: 'Active listings', value: metrics.activeListings },
    { title: 'Stock / capacity', value: `${metrics.stock}/${metrics.capacity}` },
    { title: 'Open orders', value: metrics.openOrders },
    { title: 'Proceeds (30d)', value: `£${metrics.proceeds30d}` },
    { title: 'Feedback rating', value: metrics.feedbackRating },
  ]

  return (
    <div className="min-h-screen bg-gray-50">
      <main className="p-6 max-w-7xl mx-auto space-y-8">
        {/* Metrics cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-6">
          {cards.map((c) => (
            <div key={c.title} className="bg-white shadow rounded p-4">
              <h3 className="text-sm text-gray-500">{c.title}</h3>
              <p className="text-xl font-semibold">{c.value}</p>
            </div>
          ))}
        </div>

        {/* My Listings Table */}
        <div className="bg-white shadow rounded p-4">
          <h2 className="text-lg font-semibold mb-4">My Listings</h2>
          {products.length === 0 ? (
            <p className="text-gray-500">You have no active listings yet.</p>
          ) : (
            <table className="min-w-full table-auto">
              <thead className="bg-gray-100">
                <tr>
                  <th className="px-4 py-2 text-left">Title</th>
                  <th className="px-4 py-2 text-left">Category</th>
                  <th className="px-4 py-2 text-left">Origin</th>
                  <th className="px-4 py-2 text-right">Price / kg</th>
                  <th className="px-4 py-2 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {products.map((p) => (
                  <tr key={p.id} className="border-t">
                    <td className="px-4 py-2">{p.title}</td>
                    <td className="px-4 py-2">{p.category}</td>
                    <td className="px-4 py-2">{p.origin_country}</td>
                    <td className="px-4 py-2 text-right">£{p.price_per_kg.toFixed(2)}</td>
                    <td className="px-4 py-2 text-right">
                      <Link href={`/products/edit/${p.id}`} prefetch={false}>
                        <a className="text-blue-600 hover:underline">Edit</a>
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Sell product CTA */}
        <div className="text-right">
          <Link href="/products/new" prefetch={false}>
            <a className="inline-block bg-blue-600 text-white px-4 py-2 rounded">
              + Sell Product
            </a>
          </Link>
        </div>
      </main>
    </div>
  )
}
