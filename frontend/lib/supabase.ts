import { createClient } from '@supabase/supabase-js'

// --- Supabase Client Initialization ---
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

if (!supabaseUrl || !supabaseAnonKey) {
  console.error('Supabase URL or Anon Key is missing in environment variables.')
  // In a real application, you might want to throw an error or handle this more gracefully.
  // For now, we'll ensure supabase is not used if keys are missing.
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey)

// --- Interfaces (inferred from Dashboard.tsx usage) ---
export interface Alert {
  id: string
  created_at: string
  title: string
  description: string
  severity: 'CRITICAL' | 'URGENT' | 'WARNING' | 'INFO'
  drug_name: string
  acknowledged: boolean
}

export interface Drug {
  id: string
  created_at: string
  name: string
  type: string
  criticality_rank: number
  stock_quantity: number
  usage_rate_daily: number
  burn_rate_days: number | null
  price_per_unit: number | null
  supplier_id: string | null
}

export interface Shortage {
  id: string
  created_at: string
  drug_id: string
  drug_name: string
  reason: string
  estimated_resolution: string | null
  resolved: boolean
}

// --- Utility Functions (inferred from Dashboard.tsx usage) ---

export function getSeverityColor(severity: Alert['severity']): string {
  switch (severity) {
    case 'CRITICAL':
      return 'border-red-400 text-red-800 bg-red-100'
    case 'URGENT':
      return 'border-orange-400 text-orange-800 bg-orange-100'
    case 'WARNING':
      return 'border-yellow-400 text-yellow-800 bg-yellow-100'
    case 'INFO':
      return 'border-blue-400 text-blue-800 bg-blue-100'
    default:
      return 'border-gray-400 text-gray-800 bg-gray-100'
  }
}

export function formatNumber(num: number | null): string {
  if (num === null) return 'N/A'
  return new Intl.NumberFormat().format(num)
}

export function getBurnRateColor(burnRateDays: number | null): string {
  if (burnRateDays === null) return 'text-gray-500'
  if (burnRateDays < 7) {
    return 'text-red-600 font-semibold'
  } else if (burnRateDays < 14) {
    return 'text-orange-600 font-semibold'
  } else if (burnRateDays < 30) {
    return 'text-yellow-600'
  }
  return 'text-green-600'
}
