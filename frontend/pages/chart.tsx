// frontend/pages/index.tsx
'use client';

import { useEffect, useState } from 'react';
import type { NextPage } from 'next';
import Link from 'next/link';
import dynamic from 'next/dynamic';

import api from '@/lib/api';
import Chart, { ChartPoint } from '@/components/Chart';

// 🔌 Client-only QFC canvas (WebGL)
const QFC = dynamic(
  () => import('@/components/Hologram/quantum_field_canvas'),
  { ssr: false }
);

interface Product {
  id: number;
  title: string;
  price_per_kg: number;
  origin_country: string;
  category: string;
  change_pct: number;
  rating: number;
}

const Home: NextPage = () => {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState(false);
  const [selected, setSelected] = useState<Product | null>(null);
  const [filters, setFilters]   = useState<string[]>([]);

  // ✅ New: toggle for SCI / QFC section
  const [showQFC, setShowQFC]   = useState(false);

  // 1) Fetch products on mount
  useEffect(() => {
    setLoading(true);
    api
      .get<Product[]>('/products')
      .then(({ data }) => {
        setProducts(data);
        if (data.length) setSelected(data[0]);
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, []);

  // 2) Build chart data
  const chartData: ChartPoint[] = selected
    ? Array.from({ length: 24 }, (_, i) => ({
        time:  Math.floor(Date.now() / 1000) - (23 - i) * 3600,
        value: selected.price_per_kg * 1000 + (Math.random() - 0.5) * 500,
      }))
    : [];

  // 3) Country filter logic
  const countries = Array.from(new Set(products.map(p => p.origin_country)));
  const visibleProducts = filters.length
    ? products.filter(p => filters.includes(p.origin_country))
    : products;

  return (
    <div className="min-h-screen bg-bg-page text-text-primary">
      <main className="pt-0 max-w-7xl mx-auto grid grid-cols-12 gap-6 px-4 py-6">
        {/* ─── Main Column ─────────────────────────────────────────────── */}
        <div className="col-span-12 md:col-span-9 space-y-6">
          {loading ? (
            <p className="text-center text-text-secondary">Loading…</p>
          ) : error ? (
            <p className="text-center text-red-500">Failed to load products.</p>
          ) : (
            <>
              {/* Chart Card */}
              <div className="bg-white dark:bg-gray-800 border border-border-light dark:border-gray-700 rounded-lg shadow p-4">
                {selected ? (
                  <Chart data={chartData} height={300} />
                ) : (
                  <p className="text-center text-text-secondary">
                    No product selected.
                  </p>
                )}
              </div>

              {/* Products Table Card */}
              <div className="overflow-x-auto bg-white dark:bg-gray-800 border border-border-light dark:border-gray-700 rounded-lg shadow">
                <table className="min-w-full table-auto">
                  <thead className="bg-gray-100 dark:bg-gray-700">
                    <tr>
                      <th className="px-4 py-2 text-left text-text-secondary">Product</th>
                      <th className="px-4 py-2 text-left text-text-secondary">Origin</th>
                      <th className="px-4 py-2 text-left text-text-secondary">Category</th>
                      <th className="px-4 py-2 text-right text-text-secondary">Price/kg</th>
                      <th className="px-4 py-2 text-right text-text-secondary">Change %</th>
                      <th className="px-4 py-2 text-center text-text-secondary">Rating</th>
                    </tr>
                  </thead>
                  <tbody>
                    {visibleProducts.map((p) => (
                      <tr
                        key={p.id}
                        className="border-t border-border-light dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer"
                        onClick={() => setSelected(p)}
                      >
                        <td className="px-4 py-2">
                          <Link href={`/products/${p.id}`} className="text-blue-600 hover:underline">
                            {p.title}
                          </Link>
                        </td>
                        <td className="px-4 py-2 text-text">{p.origin_country}</td>
                        <td className="px-4 py-2 text-text">{p.category}</td>
                        <td className="px-4 py-2 text-right text-text">£{p.price_per_kg.toFixed(2)}</td>
                        <td
                          className={`px-4 py-2 text-right ${
                            p.change_pct >= 0 ? 'text-green-600' : 'text-red-600'
                          }`}
                        >
                          {p.change_pct >= 0 ? '↑' : '↓'} {(Math.abs(p.change_pct) * 100).toFixed(2)}%
                        </td>
                        <td className="px-4 py-2 text-center text-text">
                          {p.rating.toFixed(1)}/5
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>

        {/* ─── Sidebar ─────────────────────────────────────────────────── */}
        <aside className="col-span-12 md:col-span-3 space-y-6">
          {selected && (
            <div className="bg-white dark:bg-gray-800 border border-border-light dark:border-gray-700 rounded-lg shadow p-4">
              <h2 className="text-xl font-semibold text-text">{selected.title}</h2>
              <p className="text-3xl font-bold text-text">
                £{(selected.price_per_kg * 1000).toFixed(2)}/t{' '}
                <span className={selected.change_pct >= 0 ? 'text-green-600' : 'text-red-600'}>
                  {selected.change_pct >= 0 ? '↑' : '↓'} {(Math.abs(selected.change_pct) * 100).toFixed(2)}%
                </span>
              </p>
            </div>
          )}

          {/* 🔘 Toggle SCI/QFC */}
          <div className="bg-white dark:bg-gray-800 border border-border-light dark:border-gray-700 rounded-lg shadow p-4">
            <h3 className="text-lg font-medium text-text mb-2">Spatial Cognition Interface</h3>
            <button
              className="px-3 py-2 rounded bg-primary/90 text-white hover:bg-primary"
              onClick={() => setShowQFC((v) => !v)}
            >
              {showQFC ? 'Hide QFC Canvas' : 'Show QFC Canvas'}
            </button>
            <p className="mt-2 text-sm text-text-secondary">
              Renders the Quantum Field Canvas (WebGL). Loads on demand.
            </p>
          </div>
        </aside>

        {/* ─── SCI / QFC Canvas Section (full-width) ───────────────────── */}
        {showQFC && (
          <section className="col-span-12">
            <div className="mt-2 rounded-lg border border-border-light dark:border-gray-700 bg-white dark:bg-gray-800 shadow">
              <div className="px-4 py-2 text-sm text-text-secondary border-b border-border-light dark:border-gray-700">
                🧠 SCI • QuantumFieldCanvas
              </div>
              <div className="h-[70vh] w-full">
                {/* Minimal props; your canvas handles presence etc. */}
                <QFC nodes={[]} links={[]} />
              </div>
            </div>
          </section>
        )}
      </main>
    </div>
  );
};

export default Home;
