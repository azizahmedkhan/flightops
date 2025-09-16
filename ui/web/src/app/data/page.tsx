'use client'

import { useState } from 'react'
import { toast } from 'react-hot-toast'
import { 
  Database, 
  Upload, 
  Loader2, 
  CheckCircle,
  AlertCircle,
  RefreshCw,
  FileText,
  Users,
  Plane,
  BarChart3
} from 'lucide-react'

interface SeedResponse {
  ok: boolean
  message: string
}

export default function DataPage() {
  const [seeding, setSeeding] = useState(false)
  const [lastSeed, setLastSeed] = useState<SeedResponse | null>(null)

  const handleSeed = async () => {
    setSeeding(true)
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_GATEWAY_URL || 'http://localhost:8080'}/demo/seed`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      })

      if (!res.ok) {
        throw new Error('Failed to seed data')
      }

      const result = await res.json()
      setLastSeed(result)
      toast.success('Data seeded successfully!')
    } catch (error) {
      toast.error('Failed to seed data. Please try again.')
      console.error('Seed error:', error)
    } finally {
      setSeeding(false)
    }
  }

  const dataTypes = [
    {
      name: 'Flights',
      description: 'Flight schedules, routes, and status information',
      icon: Plane,
      color: 'bg-blue-500',
      count: '4 flights'
    },
    {
      name: 'Bookings',
      description: 'Passenger bookings and reservations',
      icon: Users,
      color: 'bg-green-500',
      count: '6 bookings'
    },
    {
      name: 'Crew Roster',
      description: 'Crew assignments and scheduling',
      icon: Users,
      color: 'bg-purple-500',
      count: '5 crew members'
    },
    {
      name: 'Policy Documents',
      description: 'Company policies and procedures',
      icon: FileText,
      color: 'bg-orange-500',
      count: '3 documents'
    }
  ]

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between py-6">
            <div className="flex items-center space-x-3">
              <Database className="h-8 w-8 text-orange-600" />
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Data Management</h1>
                <p className="text-sm text-gray-600">Manage flight data, bookings, and crew rosters</p>
              </div>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Data Overview */}
          <div className="lg:col-span-2 space-y-6">
            {/* Data Types */}
            <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900 mb-6">Data Types</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {dataTypes.map((type) => {
                  const Icon = type.icon
                  return (
                    <div key={type.name} className="p-4 border border-gray-200 rounded-lg hover:shadow-md transition-shadow">
                      <div className="flex items-start space-x-3">
                        <div className={`${type.color} p-2 rounded-lg`}>
                          <Icon className="h-5 w-5 text-white" />
                        </div>
                        <div className="flex-1">
                          <h3 className="font-medium text-gray-900">{type.name}</h3>
                          <p className="text-sm text-gray-600 mt-1">{type.description}</p>
                          <p className="text-xs text-gray-500 mt-2">{type.count}</p>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Seed Status */}
            <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900 mb-6">Data Status</h2>
              
              {lastSeed ? (
                <div className="space-y-4">
                  <div className={`p-4 rounded-lg flex items-center ${
                    lastSeed.ok ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'
                  }`}>
                    {lastSeed.ok ? (
                      <CheckCircle className="h-5 w-5 text-green-600 mr-3" />
                    ) : (
                      <AlertCircle className="h-5 w-5 text-red-600 mr-3" />
                    )}
                    <div>
                      <p className={`font-medium ${lastSeed.ok ? 'text-green-900' : 'text-red-900'}`}>
                        {lastSeed.ok ? 'Data Seeded Successfully' : 'Seeding Failed'}
                      </p>
                      <p className={`text-sm ${lastSeed.ok ? 'text-green-700' : 'text-red-700'}`}>
                        {lastSeed.message}
                      </p>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center py-8">
                  <Database className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-500">No data seeding operations yet</p>
                </div>
              )}
            </div>
          </div>

          {/* Actions */}
          <div className="space-y-6">
            {/* Seed Data */}
            <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900 mb-6">Actions</h2>
              
              <div className="space-y-4">
                <button
                  onClick={handleSeed}
                  disabled={seeding}
                  className="w-full bg-orange-600 text-white py-3 px-4 rounded-lg hover:bg-orange-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
                >
                  {seeding ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Seeding Data...
                    </>
                  ) : (
                    <>
                      <Upload className="h-4 w-4 mr-2" />
                      Seed Demo Data
                    </>
                  )}
                </button>

                <button
                  onClick={() => window.location.reload()}
                  className="w-full bg-gray-600 text-white py-3 px-4 rounded-lg hover:bg-gray-700 flex items-center justify-center"
                >
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Refresh Status
                </button>
              </div>
            </div>

            {/* Data Statistics */}
            <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900 mb-6">Statistics</h2>
              
              <div className="space-y-4">
                <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg">
                  <div className="flex items-center">
                    <Plane className="h-5 w-5 text-blue-600 mr-2" />
                    <span className="text-sm font-medium text-blue-900">Flights</span>
                  </div>
                  <span className="text-lg font-bold text-blue-600">4</span>
                </div>
                
                <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
                  <div className="flex items-center">
                    <Users className="h-5 w-5 text-green-600 mr-2" />
                    <span className="text-sm font-medium text-green-900">Bookings</span>
                  </div>
                  <span className="text-lg font-bold text-green-600">6</span>
                </div>
                
                <div className="flex items-center justify-between p-3 bg-purple-50 rounded-lg">
                  <div className="flex items-center">
                    <Users className="h-5 w-5 text-purple-600 mr-2" />
                    <span className="text-sm font-medium text-purple-900">Crew</span>
                  </div>
                  <span className="text-lg font-bold text-purple-600">5</span>
                </div>
                
                <div className="flex items-center justify-between p-3 bg-orange-50 rounded-lg">
                  <div className="flex items-center">
                    <FileText className="h-5 w-5 text-orange-600 mr-2" />
                    <span className="text-sm font-medium text-orange-900">Documents</span>
                  </div>
                  <span className="text-lg font-bold text-orange-600">3</span>
                </div>
              </div>
            </div>

            {/* Quick Actions */}
            <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900 mb-6">Quick Actions</h2>
              
              <div className="space-y-3">
                <button className="w-full text-left p-3 text-sm text-gray-700 hover:bg-gray-50 rounded-lg border border-gray-200">
                  View Flight Schedules
                </button>
                <button className="w-full text-left p-3 text-sm text-gray-700 hover:bg-gray-50 rounded-lg border border-gray-200">
                  Check Booking Status
                </button>
                <button className="w-full text-left p-3 text-sm text-gray-700 hover:bg-gray-50 rounded-lg border border-gray-200">
                  Review Crew Assignments
                </button>
                <button className="w-full text-left p-3 text-sm text-gray-700 hover:bg-gray-50 rounded-lg border border-gray-200">
                  Browse Policy Documents
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
