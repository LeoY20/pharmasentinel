import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom'
import { useState } from 'react'
import { Activity, AlertTriangle, Package, Users, Bell, ShoppingCart } from 'lucide-react'
import Dashboard from './pages/Dashboard'
import DrugsPage from './pages/DrugsPage'
import ShortagesPage from './pages/ShortagesPage'
import SuppliersPage from './pages/SuppliersPage'
import AlertsPage from './pages/AlertsPage'
import OrdersPage from './pages/OrdersPage'

function Navigation() {
  const location = useLocation()

  const navItems = [
    { path: '/', label: 'Dashboard', icon: Activity },
    { path: '/drugs', label: 'Drugs', icon: Package },
    { path: '/shortages', label: 'Shortages', icon: AlertTriangle },
    { path: '/suppliers', label: 'Suppliers', icon: Users },
    { path: '/alerts', label: 'Alerts', icon: Bell },
    { path: '/orders', label: 'Orders', icon: ShoppingCart },
  ]


  return (
    <nav className="bg-white shadow-sm border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex">
            <div className="flex-shrink-0 flex items-center">
              <img src="/logo.png" alt="PharmaSentinel Logo" className="h-8 w-8 mr-2 rounded-lg" />
              <h1 className="text-xl font-bold text-primary-600">PharmaSentinel</h1>
            </div>
            <div className="hidden sm:ml-8 sm:flex sm:space-x-8">
              {navItems.map(({ path, label, icon: Icon }) => {
                const isActive = location.pathname === path
                return (
                  <Link
                    key={path}
                    to={path}
                    className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${isActive
                      ? 'border-primary-500 text-gray-900'
                      : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                      }`}
                  >
                    <Icon className="w-4 h-4 mr-2" />
                    {label}
                  </Link>
                )
              })}
            </div>
          </div>
          <div className="flex items-center">
            <AnalyzeButton />
          </div>
        </div>
      </div>
    </nav>
  )
}

function AnalyzeButton() {
  const [loading, setLoading] = useState(false)

  const handleAnalyze = async () => {
    setLoading(true)
    try {
      await fetch('http://localhost:8000/api/run-pipeline', {
        method: 'POST',
      })
    } catch (error) {
      console.error('Error triggering analysis:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <button
      onClick={handleAnalyze}
      disabled={loading}
      className={`inline-flex items-center px-6 py-2.5 border border-transparent text-base font-medium rounded-md shadow-sm text-white ${loading ? 'bg-primary-400 cursor-not-allowed' : 'bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500'
        }`}
    >
      {loading ? (
        <>
          <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          Analyzing...
        </>
      ) : 'Analyze'}
    </button>
  )
}

function App() {
  console.log('App component rendering');
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <Navigation />
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/drugs" element={<DrugsPage />} />
            <Route path="/shortages" element={<ShortagesPage />} />
            <Route path="/suppliers" element={<SuppliersPage />} />
            <Route path="/alerts" element={<AlertsPage />} />
            <Route path="/orders" element={<OrdersPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

export default App
