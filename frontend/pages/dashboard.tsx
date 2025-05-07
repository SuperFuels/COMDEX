// frontend/pages/dashboard.tsx

import { useRouter } from 'next/router'
import { useEffect, useState } from 'react'
import axios from 'axios'
import Chart, { ChartPoint } from '../components/Chart'

type Role = 'supplier' | 'buyer' | 'admin' | ''

export default function DashboardPage() {
  const router = useRouter()
  const [role, setRole] = useState<Role>('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const loadRole = async () => {
      const token = localStorage.getItem('token')
      if (!token) {
        router.push('/login')
        return
      }
      try {
        const { data } = await axios.get<{ role: Role }>(
          `${process.env.NEXT_PUBLIC_API_URL}/auth/role`,
          { headers: { Authorization: `Bearer ${token}` } }
        )
        setRole(data.role)
      } catch {
        router.push('/login')
      } finally {
        setLoading(false)
      }
    }
    loadRole()
  }, [router])

  if (loading) return <p className="p-8 text-center">Loading…</p>

  return (
    <main className="max-w-7xl mx-auto p-6 space-y-6 bg-gray-50 min-h-screen">
      {role === 'supplier' ? <SupplierDashboard /> : <BuyerDashboard />}
    </main>
  )
}

function SupplierDashboard() {
  // Top‐row stats
  const stats = [
    { label: "My business", value: "£0",   meta: "Today's sales"      },
    { label: "Products",    value: "0",    meta: "Active listings"    },
    { label: "Inventory",   value: "0/0",  meta: "Stock / capacity"   },
    { label: "Orders",      value: "0",    meta: "Open orders"        },
    { label: "Payments",    value: "£0",   meta: "Proceeds (30d)"     },
    { label: "Customers",   value: "0",    meta: "Feedback rating"    },
  ]

  // stubbed hourly data
  const salesData: ChartPoint[] = Array.from({ length: 24 }, (_, i) => ({
    time: Math.floor(Date.now() / 1000) - (23 - i) * 3600,
    value: Math.random() * 100,
  }))
  const ordersData: ChartPoint[] = Array.from({ length: 24 }, (_, i) => ({
    time: Math.floor(Date.now() / 1000) - (23 - i) * 3600,
    value: Math.random() * 20,
  }))

  return (
    <section className="space-y-6">
      <h1 className="text-3xl font-bold">Supplier Dashboard</h1>

      {/* Top‐row cards */}
      <div className="flex flex-wrap gap-4">
        {stats.map((s) => (
          <div
            key={s.label}
            className="flex-1 min-w-[12rem] bg-white border border-gray-200 p-4 rounded-lg shadow-sm"
          >
            <p className="text-sm font-medium text-gray-500">{s.label}</p>
            <p className="mt-1 text-2xl font-semibold text-gray-900">{s.value}</p>
            <p className="text-xs text-gray-400 mt-1">{s.meta}</p>
          </div>
        ))}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ChartCard title="Sales Over Time" data={salesData} />
        <ChartCard title="Orders Over Time" data={ordersData} />
      </div>
    </section>
  )
}

function BuyerDashboard() {
  const router = useRouter()
  const [deals, setDeals]     = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(false)

  const tabs = [
    'Quotes',
    'Deal Flow',
    'Notifications',
    'Escrow',
    'Deliveries',
    'Orders',
    'Supplier List',
  ]
  const [activeTab, setActiveTab] = useState<string>(tabs[0])

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) {
      setError(true)
      setLoading(false)
      return
    }
    axios
      .get<{ role: string }>(
        `${process.env.NEXT_PUBLIC_API_URL}/auth/role`,
        { headers: { Authorization: `Bearer ${token}` } }
      )
      .then(res => {
        if (res.data.role === 'buyer') {
          // fetch deals if needed
          setLoading(false)
        } else {
          router.push('/')
        }
      })
      .catch(() => {
        setError(true)
        setLoading(false)
      })
  }, [router])

  if (loading) return <p className="p-8 text-center">Loading your dashboard…</p>
  if (error)   return <p className="p-8 text-center text-red-500">Not authorized</p>

  // stub chart data
  const chartData: ChartPoint[] = Array.from({ length: 24 }, (_, i) => ({
    time: Math.floor(Date.now() / 1000) - (23 - i) * 3600,
    value: 500 + Math.random() * 100,
  }))

  return (
    <section className="space-y-6">
      <h1 className="text-3xl font-bold">Buyer Dashboard</h1>

      {/* Live Ask Price */}
      <div className="bg-white border border-gray-200 p-4 rounded-lg shadow-sm">
        <h2 className="text-lg font-medium text-gray-800 mb-4">
          Live Ask Price (per tonne)
        </h2>
        <Chart data={chartData} height={200} />
      </div>

      {/* Tabs */}
      <nav className="flex space-x-4 border-b border-gray-200">
        {tabs.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={
              (activeTab === tab
                ? 'border-primary text-primary'
                : 'text-gray-600 hover:text-gray-800') +
              ' pb-2 px-3 text-sm font-medium border-b-2'
            }
          >
            {tab}
          </button>
        ))}
      </nav>

      {/* Tab Content */}
      <div className="space-y-4">
        {activeTab === 'Quotes' && (
          <div className="bg-white border border-gray-200 p-4 rounded-lg shadow-sm">
            📄 You have no quotes yet.
          </div>
        )}
        {activeTab === 'Deal Flow' && (
          <div className="bg-white border border-gray-200 p-4 rounded-lg shadow-sm">
            🔄 You have no active deals.
          </div>
        )}
        {activeTab === 'Notifications' && (
          <div className="bg-white border border-gray-200 p-4 rounded-lg shadow-sm">
            🔔 No new notifications.
          </div>
        )}
        {activeTab === 'Escrow' && (
          <div className="bg-white border border-gray-200 p-4 rounded-lg shadow-sm">
            💰 No escrow transactions yet.
          </div>
        )}
        {activeTab === 'Deliveries' && (
          <div className="bg-white border border-gray-200 p-4 rounded-lg shadow-sm">
            🚚 No deliveries in transit.
          </div>
        )}
        {activeTab === 'Orders' && (
          <div className="bg-white border border-gray-200 p-4 rounded-lg shadow-sm">
            🛒 You haven’t placed any orders.
          </div>
        )}
        {activeTab === 'Supplier List' && (
          <div className="bg-white border border-gray-200 p-4 rounded-lg shadow-sm">
            ⭐ You have no saved suppliers.
          </div>
        )}
      </div>
    </section>
  )
}

function ChartCard({
  title,
  data,
}: {
  title: string
  data: ChartPoint[]
}) {
  return (
    <div className="bg-white border border-gray-200 p-4 rounded-lg shadow-sm">
      <h2 className="text-lg font-medium text-gray-800 mb-4">{title}</h2>
      <Chart data={data} height={200} />
    </div>
  )
}

