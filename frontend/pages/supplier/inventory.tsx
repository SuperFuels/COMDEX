import dynamic from 'next/dynamic'

// Dynamically load the client-only inventory page; disable SSR
export default dynamic(
  () => import('./inventory.client'),
  { ssr: false }
)
