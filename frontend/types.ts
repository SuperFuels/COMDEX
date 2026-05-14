// frontend/types.ts

export interface Deal {
  id: number
  buyer_email: string
  supplier_email: string

  // ← newly added optional wallet‐address fields
  buyer_wallet_address?: string
  supplier_wallet_address?: string

  product_title: string
  quantity_kg: number
  total_price: number
  status: string
  created_at: string
}

export interface Contract {
  id: number
  prompt: string
  generated_contract: string  // HTML string
  status: string
  created_at: string
}

