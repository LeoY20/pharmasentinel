import { createClient } from '@supabase/supabase-js'

// ============================================================================
// TypeScript Interfaces for Database Tables
// ============================================================================

export interface Drug {
  id: string
  name: string
  type: string
  stock_quantity: number
  unit: string
  price_per_unit: number | null
  primary_supplier_id: string | null
  usage_rate_daily: number
  predicted_usage_rate: number | null
  burn_rate_days: number | null
  predicted_burn_rate_days: number | null
  reorder_threshold_days: number
  criticality_rank: number
  last_restock_date: string | null
  created_at: string
  updated_at: string
}

export interface Shortage {
  id: string
  drug_name: string
  drug_id: string | null
  type: string
  source: string
  source_url: string | null
  impact_severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  description: string | null
  reported_date: string
  resolved: boolean
  resolved_date: string | null
  created_at: string
}

export interface Supplier {
  id: string
  name: string
  drug_name: string
  drug_id: string | null
  price_per_unit: number | null
  location: string | null
  lead_time_days: number | null
  reliability_score: number
  contact_info: string | null
  is_nearby_hospital: boolean
  active: boolean
  created_at: string
}

export interface Substitute {
  id: string
  drug_id: string
  drug_name: string
  substitute_name: string
  substitute_drug_id: string | null
  equivalence_notes: string | null
  preference_rank: number
  created_at: string
}

export interface AgentLog {
  id: string
  agent_name: string
  run_id: string
  payload: Record<string, any>
  summary: string | null
  created_at: string
}

export interface Alert {
  id: string
  run_id: string
  alert_type: 'RESTOCK_NOW' | 'SHORTAGE_WARNING' | 'SUBSTITUTE_RECOMMENDED' | 'SCHEDULE_CHANGE' | 'SUPPLY_CHAIN_RISK' | 'AUTO_ORDER_PLACED'
  severity: 'INFO' | 'WARNING' | 'URGENT' | 'CRITICAL'
  drug_id: string | null
  drug_name: string
  title: string
  description: string
  action_payload: Record<string, any> | null
  acknowledged: boolean
  created_at: string
}

export interface SurgerySchedule {
  id: string
  surgery_type: string
  scheduled_date: string
  estimated_duration_hours: number | null
  drugs_required: Array<{
    drug_name: string
    quantity: number
    unit: string
  }>
  status: 'SCHEDULED' | 'COMPLETED' | 'CANCELLED' | 'RESCHEDULED'
  created_at: string
}

// ============================================================================
// Database Schema Type
// ============================================================================

export interface Database {
  public: {
    Tables: {
      drugs: {
        Row: Drug
        Insert: Omit<Drug, 'id' | 'created_at' | 'updated_at'>
        Update: Partial<Omit<Drug, 'id' | 'created_at' | 'updated_at'>>
      }
      shortages: {
        Row: Shortage
        Insert: Omit<Shortage, 'id' | 'created_at'>
        Update: Partial<Omit<Shortage, 'id' | 'created_at'>>
      }
      suppliers: {
        Row: Supplier
        Insert: Omit<Supplier, 'id' | 'created_at'>
        Update: Partial<Omit<Supplier, 'id' | 'created_at'>>
      }
      substitutes: {
        Row: Substitute
        Insert: Omit<Substitute, 'id' | 'created_at'>
        Update: Partial<Omit<Substitute, 'id' | 'created_at'>>
      }
      agent_logs: {
        Row: AgentLog
        Insert: Omit<AgentLog, 'id' | 'created_at'>
        Update: Partial<Omit<AgentLog, 'id' | 'created_at'>>
      }
      alerts: {
        Row: Alert
        Insert: Omit<Alert, 'id' | 'created_at'>
        Update: Partial<Omit<Alert, 'id' | 'created_at'>>
      }
      surgery_schedule: {
        Row: SurgerySchedule
        Insert: Omit<SurgerySchedule, 'id' | 'created_at'>
        Update: Partial<Omit<SurgerySchedule, 'id' | 'created_at'>>
      }
    }
  }
}

// ============================================================================
// Supabase Client
// ============================================================================

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

if (!supabaseUrl || !supabaseAnonKey) {
  console.error('Missing Supabase environment variables. Please check your .env file.')
}

export const supabase = createClient<Database>(supabaseUrl, supabaseAnonKey)

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Get burn rate color based on days remaining
 */
export function getBurnRateColor(burnRateDays: number | null): string {
  if (!burnRateDays) return 'text-gray-400'
  if (burnRateDays < 7) return 'text-red-600 font-bold'
  if (burnRateDays < 14) return 'text-orange-600 font-semibold'
  if (burnRateDays < 30) return 'text-yellow-600'
  return 'text-green-600'
}

/**
 * Get burn rate background color based on days remaining
 */
export function getBurnRateBgColor(burnRateDays: number | null): string {
  if (!burnRateDays) return 'bg-gray-100'
  if (burnRateDays < 7) return 'bg-red-50'
  if (burnRateDays < 14) return 'bg-orange-50'
  if (burnRateDays < 30) return 'bg-yellow-50'
  return 'bg-green-50'
}

/**
 * Get severity badge color
 */
export function getSeverityColor(severity: Alert['severity']): string {
  switch (severity) {
    case 'CRITICAL':
      return 'bg-red-100 text-red-800 border-red-300'
    case 'URGENT':
      return 'bg-orange-100 text-orange-800 border-orange-300'
    case 'WARNING':
      return 'bg-yellow-100 text-yellow-800 border-yellow-300'
    case 'INFO':
      return 'bg-blue-100 text-blue-800 border-blue-300'
    default:
      return 'bg-gray-100 text-gray-800 border-gray-300'
  }
}

/**
 * Format number with commas
 */
export function formatNumber(num: number | null | undefined): string {
  if (num === null || num === undefined) return '—'
  return num.toLocaleString('en-US', { maximumFractionDigits: 1 })
}

/**
 * Format date string
 */
export function formatDate(dateString: string | null): string {
  if (!dateString) return '—'
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
}
