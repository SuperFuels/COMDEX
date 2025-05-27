import React, { useState } from 'react'
import { useRouter } from 'next/router'
import api from '@/lib/api'

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState('')

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      // Send credentials as JSON
      const payload = { email, password }

      // Hit /auth/login with JSON body
      const { data } = await api.post(
        '/auth/login',
        payload,
        { headers: { 'Content-Type': 'application/json' } }
      )

      // Store token and set Authorization header
      const token = data.token
      localStorage.setItem('token', token)
      api.defaults.headers.common.Authorization = `Bearer ${token}`

      // Redirect based on role returned by backend
      const role = data.role
      if (role === 'admin') {
        router.push('/admin/dashboard')
      } else if (role === 'supplier') {
        router.push('/supplier/dashboard')
      } else if (role === 'buyer') {
        router.push('/buyer/dashboard')
      } else {
        router.push('/')
      }
    } catch (err: any) {
      const detail = err.response?.data?.detail
      if (detail) {
        setError(
          Array.isArray(detail)
            ? detail.map((d: any) => d.msg).join(', ')
            : detail
        )
      } else {
        setError('Login failed. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <form
        onSubmit={handleLogin}
        className="bg-white p-6 rounded shadow-md w-full max-w-sm"
      >
        <h1 className="text-2xl font-bold mb-4 text-center">Login</h1>

        {error && (
          <p className="text-red-500 mb-4 text-sm text-center">{error}</p>
        )}

        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          className="border p-2 w-full mb-4 rounded"
        />

        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          className="border p-2 w-full mb-4 rounded"
        />

        <button
          type="submit"
          disabled={loading}
          className={`w-full py-2 rounded text-white ${
            loading ? 'bg-blue-400' : 'bg-blue-600 hover:bg-blue-700'
          }`}
        >
          {loading ? 'Logging in…' : 'Login'}
        </button>
      </form>
    </div>
  )
}
