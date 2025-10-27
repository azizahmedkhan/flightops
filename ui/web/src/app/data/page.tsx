'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
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
  BarChart3,
  Trash2
} from 'lucide-react'
import DataTable from '../components/DataTable'
import { 
  flightsApi, 
  bookingsApi, 
  crewRosterApi, 
  crewDetailsApi, 
  aircraftStatusApi, 
  policiesApi,
  clearAllData,
  regenerateEmbeddings,
  debugPolicies,
  forceRegenerateEmbeddings,
  Flight,
  Booking,
  CrewRoster,
  CrewDetail,
  AircraftStatus,
  Policy
} from '../services/dataApi'

interface SeedResponse {
  ok: boolean
  message: string
}

export default function DataPage() {
  const [seeding, setSeeding] = useState(false)
  const [clearing, setClearing] = useState(false)
  const [regenerating, setRegenerating] = useState(false)
  const [lastSeed, setLastSeed] = useState<SeedResponse | null>(null)
  const [lastClear, setLastClear] = useState<SeedResponse | null>(null)
  const [lastRegenerate, setLastRegenerate] = useState<SeedResponse | null>(null)
  const [activeTab, setActiveTab] = useState('flights')
  const [loading, setLoading] = useState(false)

  // Data state
  const [flights, setFlights] = useState<Flight[]>([])
  const [bookings, setBookings] = useState<Booking[]>([])
  const [crewRoster, setCrewRoster] = useState<CrewRoster[]>([])
  const [crewDetails, setCrewDetails] = useState<CrewDetail[]>([])
  const [aircraftStatus, setAircraftStatus] = useState<AircraftStatus[]>([])
  const [policies, setPolicies] = useState<Policy[]>([])

  const handleSeed = async () => {
    setSeeding(true)
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_GATEWAY_URL || 'http://localhost:8080'}/demo/seed`)

      if (!res.ok) {
        throw new Error('Failed to seed data')
      }

      const result = await res.json()
      setLastSeed(result)
      toast.success('Data seeded successfully!')
      // Refresh all data after seeding
      await loadAllData()
    } catch (error) {
      toast.error('Failed to seed data. Please try again.')
      console.error('Seed error:', error)
    } finally {
      setSeeding(false)
    }
  }

  const handleClearData = async () => {
    if (!window.confirm('Are you sure you want to clear ALL data? This action cannot be undone.')) {
      return
    }

    setClearing(true)
    try {
      const result = await clearAllData()
      setLastClear(result)
      toast.success('All data cleared successfully!')
      // Refresh all data after clearing
      await loadAllData()
    } catch (error) {
      toast.error('Failed to clear data. Please try again.')
      console.error('Clear data error:', error)
    } finally {
      setClearing(false)
    }
  }

  const handleRegenerateEmbeddings = async () => {
    setRegenerating(true)
    try {
      const result = await regenerateEmbeddings()
      setLastRegenerate(result)
      toast.success(`Embeddings regenerated for ${result.updated_count} policies!`)
      // Refresh all data after regenerating
      await loadAllData()
    } catch (error) {
      toast.error('Failed to regenerate embeddings. Please try again.')
      console.error('Regenerate embeddings error:', error)
    } finally {
      setRegenerating(false)
    }
  }

  const handleDebugPolicies = async () => {
    try {
      const result = await debugPolicies()
      console.log('Debug info:', result)
      toast.success(`Debug: ${result.total_docs} docs, ${result.total_embeddings} embeddings, ${result.docs_without_embeddings} missing embeddings`)
    } catch (error) {
      toast.error('Failed to debug policies.')
      console.error('Debug error:', error)
    }
  }

  const handleForceRegenerateEmbeddings = async () => {
    if (!window.confirm('Are you sure you want to force regenerate ALL embeddings? This will delete existing embeddings and recreate them.')) {
      return
    }

    setRegenerating(true)
    try {
      const result = await forceRegenerateEmbeddings()
      setLastRegenerate(result)
      toast.success(`Force regenerated embeddings for ${result.updated_count} policies!`)
      // Refresh all data after regenerating
      await loadAllData()
    } catch (error) {
      toast.error('Failed to force regenerate embeddings. Please try again.')
      console.error('Force regenerate embeddings error:', error)
    } finally {
      setRegenerating(false)
    }
  }

  const loadAllData = async () => {
    setLoading(true)
    try {
      const [flightsData, bookingsData, crewRosterData, crewDetailsData, aircraftStatusData, policiesData] = await Promise.all([
        flightsApi.getAll(),
        bookingsApi.getAll(),
        crewRosterApi.getAll(),
        crewDetailsApi.getAll(),
        aircraftStatusApi.getAll(),
        policiesApi.getAll()
      ])
      
      setFlights(flightsData)
      setBookings(bookingsData)
      setCrewRoster(crewRosterData)
      setCrewDetails(crewDetailsData)
      setAircraftStatus(aircraftStatusData)
      setPolicies(policiesData)
    } catch (error) {
      toast.error('Failed to load data')
      console.error('Load data error:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadAllData()
  }, [])

  const dataTypes = [
    {
      name: 'Flights',
      description: 'Flight schedules, routes, and status information',
      icon: Plane,
      color: 'bg-blue-500',
      count: `${flights.length} flights`
    },
    {
      name: 'Bookings',
      description: 'Passenger bookings and reservations',
      icon: Users,
      color: 'bg-green-500',
      count: `${bookings.length} bookings`
    },
    {
      name: 'Crew Roster',
      description: 'Crew assignments and scheduling',
      icon: Users,
      color: 'bg-gray-500',
      count: `${crewRoster.length} assignments`
    },
    {
      name: 'Policy Documents',
      description: 'Company policies and procedures',
      icon: FileText,
      color: 'bg-orange-500',
      count: `${policies.length} documents`
    }
  ]

  // Table configurations
  const flightColumns = [
    { key: 'flight_no', label: 'Flight No', type: 'text' as const, required: true },
    { key: 'flight_date', label: 'Date', type: 'date' as const, required: true },
    { key: 'origin', label: 'Origin', type: 'text' as const, required: true },
    { key: 'destination', label: 'Destination', type: 'text' as const, required: true },
    { key: 'sched_dep_time', label: 'Departure', type: 'text' as const, required: true },
    { key: 'sched_arr_time', label: 'Arrival', type: 'text' as const, required: true },
    { key: 'status', label: 'Status', type: 'select' as const, required: true, options: ['SCHEDULED', 'ON_TIME', 'DELAYED', 'CANCELLED', 'DIVERTED'] },
    { key: 'tail_number', label: 'Aircraft', type: 'text' as const, required: true }
  ]

  const bookingColumns = [
    { key: 'flight_no', label: 'Flight No', type: 'text' as const, required: true },
    { key: 'flight_date', label: 'Date', type: 'date' as const, required: true },
    { key: 'pnr', label: 'PNR', type: 'text' as const, required: true },
    { key: 'passenger_name', label: 'Passenger', type: 'text' as const, required: true },
    { key: 'has_connection', label: 'Has Connection', type: 'boolean' as const, required: true },
    { key: 'connecting_flight_no', label: 'Connecting Flight', type: 'text' as const }
  ]

  const crewRosterColumns = [
    { key: 'flight_no', label: 'Flight No', type: 'text' as const, required: true },
    { key: 'flight_date', label: 'Date', type: 'date' as const, required: true },
    { key: 'crew_id', label: 'Crew ID', type: 'text' as const, required: true },
    { key: 'crew_role', label: 'Role', type: 'select' as const, required: true, options: ['Captain', 'First Officer', 'Relief Pilot', 'Relief Captain', 'Flight Service Manager', 'Purser', 'Cabin Service Manager', 'Senior Flight Attendant', 'Flight Attendant Lead', 'Flight Attendant'] }
  ]

  const crewDetailColumns = [
    { key: 'crew_id', label: 'Crew ID', type: 'text' as const, required: true, readonly: true },
    { key: 'crew_name', label: 'Name', type: 'text' as const, required: true },
    { key: 'duty_start_time', label: 'Duty Start', type: 'text' as const, required: true },
    { key: 'max_duty_hours', label: 'Max Hours', type: 'number' as const, required: true }
  ]

  const aircraftStatusColumns = [
    { key: 'tail_number', label: 'Tail Number', type: 'text' as const, required: true, readonly: true },
    { key: 'current_location', label: 'Location', type: 'text' as const, required: true },
    { key: 'status', label: 'Status', type: 'select' as const, required: true, options: ['IN_SERVICE', 'UNDER_MAINTENANCE', 'AWAITING_CLEARANCE', 'AWAITING_DEPARTURE', 'LONG_HAUL_READY'] }
  ]

  const policyColumns = [
    { key: 'id', label: 'ID', type: 'number' as const, readonly: true },
    { key: 'title', label: 'Title', type: 'text' as const, required: true },
    { key: 'content', label: 'Content', type: 'textarea' as const, required: true },
    { key: 'meta', label: 'Metadata', type: 'json' as const },
    { key: 'embedding', label: 'Embedding', type: 'vector' as const }
  ]

  // CRUD handlers
  const handleFlightAdd = async (data: any) => {
    await flightsApi.create(data)
    await loadAllData()
  }

  const handleFlightEdit = async (id: string, data: any) => {
    await flightsApi.update(id, data)
    await loadAllData()
  }

  const handleFlightDelete = async (id: string) => {
    await flightsApi.delete(id)
    await loadAllData()
  }

  const handleBookingAdd = async (data: any) => {
    await bookingsApi.create(data)
    await loadAllData()
  }

  const handleBookingEdit = async (id: string, data: any) => {
    await bookingsApi.update(id, data)
    await loadAllData()
  }

  const handleBookingDelete = async (id: string) => {
    await bookingsApi.delete(id)
    await loadAllData()
  }

  const handleCrewRosterAdd = async (data: any) => {
    await crewRosterApi.create(data)
    await loadAllData()
  }

  const handleCrewRosterEdit = async (id: string, data: any) => {
    const [flight_no, crew_id] = id.split('|')
    await crewRosterApi.update(flight_no, crew_id, data)
    await loadAllData()
  }

  const handleCrewRosterDelete = async (id: string) => {
    const [flight_no, crew_id] = id.split('|')
    await crewRosterApi.delete(flight_no, crew_id)
    await loadAllData()
  }

  const handleCrewDetailAdd = async (data: any) => {
    await crewDetailsApi.create(data)
    await loadAllData()
  }

  const handleCrewDetailEdit = async (id: string, data: any) => {
    await crewDetailsApi.update(id, data)
    await loadAllData()
  }

  const handleCrewDetailDelete = async (id: string) => {
    await crewDetailsApi.delete(id)
    await loadAllData()
  }

  const handleAircraftStatusAdd = async (data: any) => {
    await aircraftStatusApi.create(data)
    await loadAllData()
  }

  const handleAircraftStatusEdit = async (id: string, data: any) => {
    await aircraftStatusApi.update(id, data)
    await loadAllData()
  }

  const handleAircraftStatusDelete = async (id: string) => {
    await aircraftStatusApi.delete(id)
    await loadAllData()
  }

  const handlePolicyAdd = async (data: any) => {
    await policiesApi.create(data)
    await loadAllData()
  }

  const handlePolicyEdit = async (id: string, data: any) => {
    await policiesApi.update(id, data)
    await loadAllData()
  }

  const handlePolicyDelete = async (id: string) => {
    await policiesApi.delete(id)
    await loadAllData()
  }

  // Transform crew roster data to include composite key
  const crewRosterWithKeys = crewRoster.map(item => ({
    ...item,
    composite_key: `${item.flight_no}|${item.crew_id}`
  }))

  return (
    <div className="min-h-screen relative">
      {/* Header */}
      <header className="bg-black text-white relative z-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between py-6">
            <div className="flex items-center space-x-3">
              <div className="bg-white p-2 rounded-lg">
                <Database className="h-6 w-6 text-black" />
              </div>
              <div>
                <h1 className="text-2xl font-bold">Data Management</h1>
                <p className="text-sm text-gray-300">Manage flight data, bookings, and crew rosters</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <button
                onClick={handleDebugPolicies}
                className="bg-gray-600 text-white py-2 px-4 rounded-lg hover:bg-gray-700 flex items-center font-semibold transition-colors"
              >
                <BarChart3 className="h-4 w-4 mr-2" />
                Debug
              </button>
              <button
                onClick={handleRegenerateEmbeddings}
                disabled={regenerating}
                className="bg-gray-600 text-white py-2 px-4 rounded-lg hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center font-semibold transition-colors"
              >
                {regenerating ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Regenerating...
                  </>
                ) : (
                  <>
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Regenerate Embeddings
                  </>
                )}
              </button>
              <button
                onClick={handleForceRegenerateEmbeddings}
                disabled={regenerating}
                className="bg-orange-600 text-white py-2 px-4 rounded-lg hover:bg-orange-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center font-semibold transition-colors"
              >
                {regenerating ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Force Regenerating...
                  </>
                ) : (
                  <>
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Force Regenerate
                  </>
                )}
              </button>
              <button
                onClick={handleClearData}
                disabled={clearing}
                className="bg-red-600 text-white py-2 px-4 rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center font-semibold transition-colors"
              >
                {clearing ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Clearing...
                  </>
                ) : (
                  <>
                    <Trash2 className="h-4 w-4 mr-2" />
                    Clear Data
                  </>
                )}
              </button>
              <button
                onClick={handleSeed}
                disabled={seeding}
                className="bg-white text-black py-2 px-4 rounded-lg hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed flex items-center font-semibold transition-colors"
              >
                {seeding ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Seeding...
                  </>
                ) : (
                  <>
                    <Upload className="h-4 w-4 mr-2" />
                    Seed Data
                  </>
                )}
              </button>
              <Link href="/" className="text-sm font-medium text-white hover:text-gray-200">
                Back to Home
              </Link>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 relative z-10">
        {/* Data Overview Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                {dataTypes.map((type) => {
                  const Icon = type.icon
                  return (
              <div key={type.name} className="bg-white/95 backdrop-blur-sm rounded-xl shadow-lg p-6 border-2 border-gray-200 hover:shadow-xl transition-all duration-200">
                      <div className="flex items-start space-x-3">
                  <div className={`${type.color} p-3 rounded-lg`}>
                    <Icon className="h-6 w-6 text-white" />
                        </div>
                        <div className="flex-1">
                    <h3 className="font-bold text-black text-lg">{type.name}</h3>
                    <p className="text-sm text-gray-600 mt-1">{type.description}</p>
                    <p className="text-lg font-bold text-gray-800 mt-2">{type.count}</p>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>

        {/* Tab Navigation */}
        <div className="bg-white/95 backdrop-blur-sm rounded-xl shadow-lg border-2 border-gray-200 mb-6">
          <div className="border-b border-gray-200">
            <nav className="flex space-x-8 px-6" aria-label="Tabs">
              {[
                { id: 'flights', name: 'Flights', icon: Plane },
                { id: 'bookings', name: 'Bookings', icon: Users },
                { id: 'crew_roster', name: 'Crew Roster', icon: Users },
                { id: 'crew_details', name: 'Crew Details', icon: Users },
                { id: 'aircraft_status', name: 'Aircraft Status', icon: Plane },
                { id: 'policies', name: 'Policies', icon: FileText }
              ].map((tab) => {
                const Icon = tab.icon
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`${
                      activeTab === tab.id
                        ? 'border-blue-500 text-blue-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                    } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm flex items-center space-x-2`}
                  >
                    <Icon className="h-4 w-4" />
                    <span>{tab.name}</span>
                  </button>
                )
              })}
            </nav>
          </div>
        </div>

        {/* Tab Content */}
        <div className="space-y-6">
          {activeTab === 'flights' && (
            <DataTable
              title="Flights"
              columns={flightColumns}
              data={flights}
              loading={loading}
              onAdd={handleFlightAdd}
              onEdit={handleFlightEdit}
              onDelete={handleFlightDelete}
              onRefresh={loadAllData}
              primaryKey="flight_no"
            />
          )}

          {activeTab === 'bookings' && (
            <DataTable
              title="Bookings"
              columns={bookingColumns}
              data={bookings}
              loading={loading}
              onAdd={handleBookingAdd}
              onEdit={handleBookingEdit}
              onDelete={handleBookingDelete}
              onRefresh={loadAllData}
              primaryKey="pnr"
            />
          )}

          {activeTab === 'crew_roster' && (
            <DataTable
              title="Crew Roster"
              columns={crewRosterColumns}
              data={crewRosterWithKeys}
              loading={loading}
              onAdd={handleCrewRosterAdd}
              onEdit={handleCrewRosterEdit}
              onDelete={handleCrewRosterDelete}
              onRefresh={loadAllData}
              primaryKey="composite_key"
            />
          )}

          {activeTab === 'crew_details' && (
            <DataTable
              title="Crew Details"
              columns={crewDetailColumns}
              data={crewDetails}
              loading={loading}
              onAdd={handleCrewDetailAdd}
              onEdit={handleCrewDetailEdit}
              onDelete={handleCrewDetailDelete}
              onRefresh={loadAllData}
              primaryKey="crew_id"
            />
          )}

          {activeTab === 'aircraft_status' && (
            <DataTable
              title="Aircraft Status"
              columns={aircraftStatusColumns}
              data={aircraftStatus}
              loading={loading}
              onAdd={handleAircraftStatusAdd}
              onEdit={handleAircraftStatusEdit}
              onDelete={handleAircraftStatusDelete}
              onRefresh={loadAllData}
              primaryKey="tail_number"
            />
          )}

          {activeTab === 'policies' && (
            <DataTable
              title="Policies"
              columns={policyColumns}
              data={policies}
              loading={loading}
              onAdd={handlePolicyAdd}
              onEdit={handlePolicyEdit}
              onDelete={handlePolicyDelete}
              onRefresh={loadAllData}
              primaryKey="id"
            />
          )}
            </div>

        {/* Operation Status */}
        {(lastSeed || lastClear || lastRegenerate) && (
          <div className="mt-8 bg-white/95 backdrop-blur-sm rounded-xl shadow-lg p-6 border-2 border-gray-200">
            <h2 className="text-xl font-bold text-black mb-4">Last Operation</h2>
            <div className="space-y-4">
              {lastSeed && (
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
              )}
              
              {lastClear && (
                <div className={`p-4 rounded-lg flex items-center ${
                  lastClear.ok ? 'bg-orange-50 border border-orange-200' : 'bg-red-50 border border-red-200'
                }`}>
                  {lastClear.ok ? (
                    <CheckCircle className="h-5 w-5 text-orange-600 mr-3" />
                  ) : (
                    <AlertCircle className="h-5 w-5 text-red-600 mr-3" />
                  )}
                  <div>
                    <p className={`font-medium ${lastClear.ok ? 'text-orange-900' : 'text-red-900'}`}>
                      {lastClear.ok ? 'Data Cleared Successfully' : 'Clear Failed'}
                    </p>
                    <p className={`text-sm ${lastClear.ok ? 'text-orange-700' : 'text-red-700'}`}>
                      {lastClear.message}
                    </p>
                  </div>
                </div>
              )}

              {lastRegenerate && (
                <div className={`p-4 rounded-lg flex items-center ${
                  lastRegenerate.ok ? 'bg-gray-50 border border-gray-200' : 'bg-red-50 border border-red-200'
                }`}>
                  {lastRegenerate.ok ? (
                    <CheckCircle className="h-5 w-5 text-gray-600 mr-3" />
                  ) : (
                    <AlertCircle className="h-5 w-5 text-red-600 mr-3" />
                  )}
                  <div>
                    <p className={`font-medium ${lastRegenerate.ok ? 'text-gray-900' : 'text-red-900'}`}>
                      {lastRegenerate.ok ? 'Embeddings Regenerated Successfully' : 'Regeneration Failed'}
                    </p>
                    <p className={`text-sm ${lastRegenerate.ok ? 'text-gray-700' : 'text-red-700'}`}>
                      {lastRegenerate.message}
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
