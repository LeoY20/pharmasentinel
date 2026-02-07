import { useEffect, useState } from 'react'
import { AlertTriangle, ShieldAlert, TrendingDown, Package } from 'lucide-react'
import { supabase, Alert, Drug, Shortage, getSeverityColor, formatNumber, getBurnRateColor } from '../lib/supabase'

export default function Dashboard() {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [drugs, setDrugs] = useState<Drug[]>([])
  const [shortages, setShortages] = useState<Shortage[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchData()

    // Subscribe to realtime updates
    const alertsChannel = supabase
      .channel('alerts-channel')
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'alerts' }, (payload) => {
        setAlerts((prev) => [payload.new as Alert, ...prev])
      })
      .subscribe()

    const drugsChannel = supabase
      .channel('drugs-channel')
      .on('postgres_changes', { event: 'UPDATE', schema: 'public', table: 'drugs' }, (payload) => {
        setDrugs((prev) => prev.map((d) => (d.id === payload.new.id ? (payload.new as Drug) : d)))
      })
      .subscribe()

    return () => {
      alertsChannel.unsubscribe()
      drugsChannel.unsubscribe()
    }
  }, [])

  async function fetchData() {
    setLoading(true)

    const [alertsRes, drugsRes, shortagesRes] = await Promise.all([
      supabase.from('alerts').select('*').eq('acknowledged', false).order('created_at', { ascending: false }),
      supabase.from('drugs').select('*').order('criticality_rank'),
      supabase.from('shortages').select('*').eq('resolved', false),
    ])

    if (alertsRes.data) setAlerts(alertsRes.data)
    if (drugsRes.data) setDrugs(drugsRes.data)
    if (shortagesRes.data) setShortages(shortagesRes.data)

    setLoading(false)
  }

  async function acknowledgeAlert(alertId: string) {
    await supabase.from('alerts').update({ acknowledged: true }).eq('id', alertId)
    setAlerts((prev) => prev.filter((a) => a.id !== alertId))
  }

  const criticalAlerts = alerts.filter((a) => a.severity === 'CRITICAL').length
  const urgentAlerts = alerts.filter((a) => a.severity === 'URGENT').length
  const lowStockDrugs = drugs.filter((d) => (d.burn_rate_days ?? 999) < 14).length
  const activeShortages = shortages.length

  if (loading) {
    return <div className="text-center py-12">Loading...</div>
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500">Hospital pharmacy supply chain overview</p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <SummaryCard title="Critical Alerts" value={criticalAlerts} icon={ShieldAlert} color="red" />
        <SummaryCard title="Urgent Alerts" value={urgentAlerts} icon={AlertTriangle} color="orange" />
        <SummaryCard title="Low Stock Drugs" value={lowStockDrugs} icon={TrendingDown} color="yellow" />
        <SummaryCard title="Active Shortages" value={activeShortages} icon={Package} color="blue" />
      </div>

      {/* Active Alerts */}
      <div className="bg-white shadow-sm rounded-lg p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Active Alerts</h2>
        {alerts.length === 0 ? (
          <p className="text-gray-500 text-center py-8">No active alerts</p>
        ) : (
          <div className="space-y-3">
            {alerts.map((alert) => (
              <div
                key={alert.id}
                className={`border-l-4 p-4 rounded ${
                  alert.severity === 'CRITICAL'
                    ? 'border-red-500 bg-red-50'
                    : alert.severity === 'URGENT'
                    ? 'border-orange-500 bg-orange-50'
                    : alert.severity === 'WARNING'
                    ? 'border-yellow-500 bg-yellow-50'
                    : 'border-blue-500 bg-blue-50'
                }`}
              >
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium border ${getSeverityColor(alert.severity)}`}>
                        {alert.severity}
                      </span>
                      <span className="text-xs text-gray-500">{alert.drug_name}</span>
                    </div>
                    <h3 className="font-medium text-gray-900">{alert.title}</h3>
                    <p className="text-sm text-gray-600 mt-1">{alert.description}</p>
                  </div>
                  <button
                    onClick={() => acknowledgeAlert(alert.id)}
                    className="ml-4 px-3 py-1 text-sm bg-white border border-gray-300 rounded hover:bg-gray-50"
                  >
                    Acknowledge
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Drug Inventory Table */}
      <div className="bg-white shadow-sm rounded-lg p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Drug Inventory</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead>
              <tr>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Rank</th>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Drug</th>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                <th className="px-3 py-2 text-right text-xs font-medium text-gray-500 uppercase">Stock</th>
                <th className="px-3 py-2 text-right text-xs font-medium text-gray-500 uppercase">Daily Usage</th>
                <th className="px-3 py-2 text-right text-xs font-medium text-gray-500 uppercase">Burn Rate</th>
                <th className="px-3 py-2 text-right text-xs font-medium text-gray-500 uppercase">Price/Unit</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {drugs.map((drug) => (
                <tr key={drug.id} className="hover:bg-gray-50">
                  <td className="px-3 py-2 text-sm">{drug.criticality_rank}</td>
                  <td className="px-3 py-2 text-sm font-medium text-gray-900">{drug.name}</td>
                  <td className="px-3 py-2 text-sm text-gray-500">{drug.type}</td>
                  <td className="px-3 py-2 text-sm text-right">
                    {formatNumber(drug.stock_quantity)} {drug.unit}
                  </td>
                  <td className="px-3 py-2 text-sm text-right">{formatNumber(drug.usage_rate_daily)}</td>
                  <td className={`px-3 py-2 text-sm text-right ${getBurnRateColor(drug.burn_rate_days)}`}>
                    {drug.burn_rate_days ? `${formatNumber(drug.burn_rate_days)} days` : '—'}
                  </td>
                  <td className="px-3 py-2 text-sm text-right">${formatNumber(drug.price_per_unit ?? 0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

interface SummaryCardProps {
  title: string
  value: number
  icon: React.ElementType
  color: 'red' | 'orange' | 'yellow' | 'blue'
}

function SummaryCard({ title, value, icon: Icon, color }: SummaryCardProps) {
  const colorClasses = {
    red: 'bg-red-100 text-red-600',
    orange: 'bg-orange-100 text-orange-600',
    yellow: 'bg-yellow-100 text-yellow-600',
    blue: 'bg-blue-100 text-blue-600',
  }

  return (
    <div className="bg-white shadow-sm rounded-lg p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-500">{title}</p>
          <p className="mt-2 text-3xl font-bold text-gray-900">{value}</p>
        </div>
        <div className={`p-3 rounded-lg ${colorClasses[color]}`}>
          <Icon className="w-6 h-6" />
        </div>
      </div>
    </div>
  )
}
