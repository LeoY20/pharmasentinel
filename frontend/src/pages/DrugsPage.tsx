import { useEffect, useState } from 'react'
import { supabase, Drug, formatNumber, getBurnRateColor, getBurnRateBgColor } from '../lib/supabase'

export default function DrugsPage() {
  const [drugs, setDrugs] = useState<Drug[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchDrugs()
  }, [])

  async function fetchDrugs() {
    const { data } = await supabase.from('drugs').select('*').order('criticality_rank')
    if (data) setDrugs(data)
    setLoading(false)
  }

  if (loading) return <div className="text-center py-12">Loading...</div>

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-900">Drug Inventory</h1>

      <div className="bg-white shadow-sm rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Rank</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Drug Name</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Stock</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Daily Usage</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Predicted Usage</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Burn Rate</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Predicted Burn</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {drugs.map((drug) => (
              <tr key={drug.id} className={`hover:bg-gray-50 ${getBurnRateBgColor(drug.predicted_burn_rate_days ?? drug.burn_rate_days)}`}>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{drug.criticality_rank}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-bold text-gray-900">{drug.name}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{drug.type}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-right">
                  {formatNumber(drug.stock_quantity)} {drug.unit}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-right">{formatNumber(drug.usage_rate_daily)}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-right">{formatNumber(drug.predicted_usage_rate)}</td>
                <td className={`px-6 py-4 whitespace-nowrap text-sm text-right ${getBurnRateColor(drug.burn_rate_days)}`}>
                  {drug.burn_rate_days ? `${formatNumber(drug.burn_rate_days)} days` : '—'}
                </td>
                <td className={`px-6 py-4 whitespace-nowrap text-sm text-right ${getBurnRateColor(drug.predicted_burn_rate_days)}`}>
                  {drug.predicted_burn_rate_days ? `${formatNumber(drug.predicted_burn_rate_days)} days` : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
