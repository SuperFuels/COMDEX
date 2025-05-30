// frontend/pages/supplier/dashboard.tsx
import Link from 'next/link'
import useAuthRedirect from '@/hooks/useAuthRedirect'
import useSupplierDashboard from '@/hooks/useSupplierDashboard'

export default function SupplierDashboard() {
  // only suppliers allowed here
  useAuthRedirect('supplier')

  const { data, loading, error } = useSupplierDashboard()

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-gray-600">Loading dashboard…</p>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-red-600">{error || 'Unknown error'}</p>
      </div>
    )
  }

  const cards = [
    { label: 'Sales Today', value: data.totalSalesToday },
    { label: 'Active Listings', value: data.activeListings },
    { label: 'Open Orders', value: data.openOrders },
    { label: '30d Proceeds', value: `£${data.proceeds30d}` },
    { label: 'Feedback', value: data.feedbackRating },
  ]

  return (
    <div className="min-h-screen bg-gray-50">
      <main className="p-6 max-w-7xl mx-auto space-y-8">
        {/* Metrics cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-6">
          {cards.map((c) => (
            <div key={c.label} className="bg-white shadow rounded p-4">
              <p className="text-gray-500">{c.label}</p>
              <p className="mt-2 text-2xl font-semibold">{c.value}</p>
            </div>
          ))}
        </div>

        {/* Charts section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white shadow rounded p-4 h-64 flex items-center justify-center text-gray-400">
            Chart placeholder
          </div>
          <div className="bg-white shadow rounded p-4 h-64 flex items-center justify-center text-gray-400">
            Chart placeholder
          </div>
        </div>

        {/* My Listings Table */}
        <div className="bg-white shadow rounded p-4">
          <h2 className="text-lg font-semibold mb-4">My Listings</h2>
          {data.products.length === 0 ? (
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
                {data.products.map((p) => (
                  <tr key={p.id} className="border-t">
                    <td className="px-4 py-2">{p.title}</td>
                    <td className="px-4 py-2">{p.category}</td>
                    <td className="px-4 py-2">{p.origin_country}</td>
                    <td className="px-4 py-2 text-right">
                      £{p.price_per_kg.toFixed(2)}
                    </td>
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