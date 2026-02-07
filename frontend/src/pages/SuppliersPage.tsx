import { useEffect, useState } from 'react'
import { supabase, Supplier, formatNumber } from '../lib/supabase'

export default function SuppliersPage() {
  const [suppliers, setSuppliers] = useState<Supplier[]>([])

  useEffect(() => {
    fetchSuppliers()
  }, [])

  async function fetchSuppliers() {
    const { data } = await supabase.from('suppliers').select('*').eq('active', true).order('name')
    if (data) setSuppliers(data)
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-900">Suppliers</h1>

      <div className="bg-white shadow-sm rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Drug</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Location</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Price/Unit</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Lead Time</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Reliability</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {suppliers.map((supplier) => (
              <tr key={supplier.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 text-sm font-medium text-gray-900">{supplier.name}</td>
                <td className="px-6 py-4 text-sm text-gray-500">{supplier.drug_name}</td>
                <td className="px-6 py-4 text-sm text-gray-500">{supplier.location || '—'}</td>
                <td className="px-6 py-4 text-sm text-right">${formatNumber(supplier.price_per_unit)}</td>
                <td className="px-6 py-4 text-sm text-right">{supplier.lead_time_days ?? '—'} days</td>
                <td className="px-6 py-4 text-sm text-right">{formatNumber(supplier.reliability_score * 100)}%</td>
                <td className="px-6 py-4 text-sm">
                  <span className={`px-2 py-1 rounded text-xs font-medium ${supplier.is_nearby_hospital ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-800'}`}>
                    {supplier.is_nearby_hospital ? 'Hospital' : 'Vendor'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
