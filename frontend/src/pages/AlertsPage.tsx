import { useEffect, useState } from 'react'
import { supabase, Alert, formatDate, getSeverityColor } from '../lib/supabase'

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [filter, setFilter] = useState<'all' | 'active' | 'acknowledged'>('all')

  useEffect(() => {
    fetchAlerts()
  }, [filter])

  async function fetchAlerts() {
    let query = supabase.from('alerts').select('*').order('created_at', { ascending: false })

    if (filter === 'active') query = query.eq('acknowledged', false)
    if (filter === 'acknowledged') query = query.eq('acknowledged', true)

    const { data } = await query
    if (data) setAlerts(data)
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-900">Alert History</h1>
        <div className="flex gap-2">
          {(['all', 'active', 'acknowledged'] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-4 py-2 rounded-lg text-sm font-medium ${
                filter === f ? 'bg-primary-600 text-white' : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
              }`}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-3">
        {alerts.map((alert) => (
          <div key={alert.id} className="bg-white shadow-sm rounded-lg p-6">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <span className={`px-2 py-1 rounded text-xs font-medium border ${getSeverityColor(alert.severity)}`}>
                    {alert.severity}
                  </span>
                  <span className="px-2 py-1 rounded text-xs font-medium bg-gray-100 text-gray-800">
                    {alert.alert_type.replace(/_/g, ' ')}
                  </span>
                  <span className="text-sm text-gray-500">{alert.drug_name}</span>
                </div>
                <h3 className="text-lg font-medium text-gray-900">{alert.title}</h3>
                <p className="text-sm text-gray-600 mt-1">{alert.description}</p>
                <p className="text-xs text-gray-400 mt-2">{formatDate(alert.created_at)}</p>
              </div>
              <div>
                {alert.acknowledged ? (
                  <span className="px-3 py-1 rounded text-sm bg-green-100 text-green-800">Acknowledged</span>
                ) : (
                  <span className="px-3 py-1 rounded text-sm bg-yellow-100 text-yellow-800">Pending</span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
