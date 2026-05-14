'use client'

import { useState, useEffect } from 'react'
import Head from 'next/head'
import api from '@/lib/api'

export default function VaultPage() {
  const [containerId, setContainerId] = useState('')
  const [associatedData, setAssociatedData] = useState('')
  const [snapshots, setSnapshots] = useState<string[]>([])
  const [selectedSnapshot, setSelectedSnapshot] = useState('')
  const [status, setStatus] = useState<'idle' | 'loading' | 'done' | 'error'>('idle')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const fetchSnapshots = async () => {
    setStatus('loading')
    setErrorMessage(null)
    try {
      const url = containerId ? `vault/list?container_id=${encodeURIComponent(containerId)}` : 'vault/list'
      const res = await api.get(url)
      if (res.status !== 200) throw new Error('Failed to fetch snapshots')
      setSnapshots(res.data.snapshots || [])
      setStatus('done')
    } catch (err: any) {
      setErrorMessage(err.message || 'Unknown error fetching snapshots')
      setStatus('error')
    }
  }

  useEffect(() => {
    fetchSnapshots()
  }, [containerId])

  const saveSnapshot = async () => {
    if (!containerId) {
      setErrorMessage('Container ID is required to save a snapshot')
      return
    }
    setStatus('loading')
    setErrorMessage(null)
    try {
      const res = await api.post('vault/save', {
        container_id: containerId,
        associated_data: associatedData || undefined,
      })
      if (res.status !== 200) throw new Error(res.data.detail || 'Failed to save snapshot')
      setStatus('done')
      setErrorMessage(null)
      setSnapshots((prev) => [res.data.filename, ...prev])
    } catch (err: any) {
      setErrorMessage(err.message || 'Error saving snapshot')
      setStatus('error')
    }
  }

  const restoreSnapshot = async () => {
    if (!selectedSnapshot) {
      setErrorMessage('Please select a snapshot to restore')
      return
    }
    setStatus('loading')
    setErrorMessage(null)
    try {
      const res = await api.post('vault/restore', {
        filename: selectedSnapshot,
        associated_data: associatedData || undefined,
      })
      if (res.status !== 200) throw new Error(res.data.detail || 'Failed to restore snapshot')
      setStatus('done')
      setErrorMessage(null)
    } catch (err: any) {
      setErrorMessage(err.message || 'Error restoring snapshot')
      setStatus('error')
    }
  }

  const deleteSnapshot = async () => {
    if (!selectedSnapshot) {
      setErrorMessage('Please select a snapshot to delete')
      return
    }
    setStatus('loading')
    setErrorMessage(null)
    try {
      const res = await api.delete('vault/delete', {
        data: { filename: selectedSnapshot },
      })
      if (res.status !== 200) throw new Error(res.data.detail || 'Failed to delete snapshot')
      setStatus('done')
      setErrorMessage(null)
      setSnapshots((prev) => prev.filter((f) => f !== selectedSnapshot))
      setSelectedSnapshot('')
    } catch (err: any) {
      setErrorMessage(err.message || 'Error deleting snapshot')
      setStatus('error')
    }
  }

  return (
    <>
      <Head>
        <title>Vault Snapshots • AION</title>
      </Head>
      <div className="p-8 max-w-5xl mx-auto space-y-6">
        <h1 className="text-3xl font-bold flex items-center space-x-2">
          <span>🔐 Vault Snapshot Manager</span>
        </h1>

        {/* Container ID and Auth Data Inputs */}
        <div className="space-y-4">
          <input
            type="text"
            placeholder="Container ID"
            value={containerId}
            onChange={(e) => setContainerId(e.target.value)}
            className="w-full p-3 border border-gray-300 rounded-lg shadow-sm dark:bg-gray-800 dark:text-white dark:border-gray-600"
          />
          <input
            type="text"
            placeholder="Associated Auth Data (hex, optional)"
            value={associatedData}
            onChange={(e) => setAssociatedData(e.target.value)}
            className="w-full p-3 border border-gray-300 rounded-lg shadow-sm dark:bg-gray-800 dark:text-white dark:border-gray-600"
          />
          <button
            onClick={saveSnapshot}
            disabled={!containerId || status === 'loading'}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {status === 'loading' ? 'Saving...' : 'Save Snapshot'}
          </button>
        </div>

        <hr className="border-gray-300 dark:border-gray-700" />

        {/* Snapshots List */}
        <div>
          <h2 className="text-xl font-semibold mb-3">Snapshots</h2>
          {snapshots.length === 0 ? (
            <p className="text-gray-500">No snapshots found.</p>
          ) : (
            <select
              value={selectedSnapshot}
              onChange={(e) => setSelectedSnapshot(e.target.value)}
              size={6}
              className="w-full p-3 border border-gray-300 rounded-lg dark:bg-gray-800 dark:text-white dark:border-gray-600"
            >
              {snapshots.map((filename) => (
                <option key={filename} value={filename}>
                  {filename}
                </option>
              ))}
            </select>
          )}
          <div className="mt-4 flex gap-4">
            <button
              onClick={restoreSnapshot}
              disabled={!selectedSnapshot || status === 'loading'}
              className="flex-1 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
            >
              Restore Selected
            </button>
            <button
              onClick={deleteSnapshot}
              disabled={!selectedSnapshot || status === 'loading'}
              className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
            >
              Delete Selected
            </button>
          </div>
        </div>

        {/* Status and Errors */}
        <div>
          {status === 'done' && !errorMessage && (
            <p className="text-green-600 font-medium">Operation completed successfully.</p>
          )}
          {status === 'error' && errorMessage && (
            <p className="text-red-600 font-medium">Error: {errorMessage}</p>
          )}
        </div>
      </div>
    </>
  )
}