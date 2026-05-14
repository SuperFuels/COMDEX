// File: frontend/hooks/useSupplierDashboard.ts

import { useState, useEffect } from 'react'
import api from '@/lib/api'

export default function useSupplierDashboard() {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchDashboard() {
      try {
        // Explicitly call your Cloud Run backend via the NEXT_PUBLIC_API_URL
        // For example, if NEXT_PUBLIC_API_URL="https://comdex-api-XXXX.us-central1.run.app/api"
        const endpoint = `${process.env.NEXT_PUBLIC_API_URL}/supplier/dashboard`
        const resp = await api.get(endpoint)
        setData(resp.data)
      } catch (err: any) {
        setError(err.message || 'Error fetching data')
      } finally {
        setLoading(false)
      }
    }

    fetchDashboard()
  }, [])

  return { data, loading, error }
}