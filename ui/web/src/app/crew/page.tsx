'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'react-hot-toast'
import { 
  Users, 
  UserCheck, 
  AlertTriangle, 
  Clock, 
  Plane, 
  Wrench,
  CheckCircle,
  XCircle,
  Loader2,
  Search,
  RefreshCw,
  Shield
} from 'lucide-react'

const crewOptimizationSchema = z.object({
  flight_no: z.string().min(1, 'Flight number is required'),
  date: z.string().min(1, 'Date is required'),
  disruption_type: z.string().optional(),
  time_constraint: z.number().optional()
})

const crewSwapSchema = z.object({
  flight_no: z.string().min(1, 'Flight number is required'),
  date: z.string().min(1, 'Date is required'),
  unavailable_crew_id: z.string().min(1, 'Crew ID is required'),
  reason: z.string().min(1, 'Reason is required')
})

type CrewOptimizationForm = z.infer<typeof crewOptimizationSchema>
type CrewSwapForm = z.infer<typeof crewSwapSchema>

interface CrewMember {
  crew_id: string
  name: string
  role: string
  qualifications: string[]
  current_location: string
  duty_hours: number
  max_duty_hours: number
  rest_required: number
  availability_status: string
  last_flight?: string
  is_legal?: boolean
  violations?: string[]
}

interface CrewOptimizationResult {
  flight_no: string
  date: string
  crew_analysis: {
    risk_level: string
    concerns: string[]
    recommendations: string[]
    priority: number
    estimated_resolution_time: string
  }
  crew_members: CrewMember[]
  recommendations: string[]
  optimization_status: string
}

interface CrewSwapResult {
  flight_no: string
  date: string
  unavailable_crew: string
  swap_suggestions: any[]
  recommended_swap: any
}

export default function CrewPage() {
  const [optimizationResults, setOptimizationResults] = useState<CrewOptimizationResult[]>([])
  const [swapResults, setSwapResults] = useState<CrewSwapResult[]>([])
  const [availableCrew, setAvailableCrew] = useState<CrewMember[]>([])
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<'optimize' | 'swap' | 'availability'>('optimize')

  const optimizationForm = useForm<CrewOptimizationForm>({
    resolver: zodResolver(crewOptimizationSchema),
    defaultValues: {
      flight_no: 'NZ123',
      date: '2025-09-17',
      disruption_type: 'weather_delay',
      time_constraint: 2
    }
  })

  const swapForm = useForm<CrewSwapForm>({
    resolver: zodResolver(crewSwapSchema),
    defaultValues: {
      flight_no: 'NZ123',
      date: '2025-09-17',
      unavailable_crew_id: 'CAP001',
      reason: 'illness'
    }
  })

  const optimizeCrew = async (data: CrewOptimizationForm) => {
    setLoading(true)
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_GATEWAY_URL || 'http://localhost:8080'}/crew/optimize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      })

      if (!res.ok) throw new Error('Failed to optimize crew')
      
      const result = await res.json()
      setOptimizationResults(prev => [result, ...prev])
      toast.success('Crew optimization completed!')
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred'
      toast.error(`Failed to optimize crew: ${errorMessage}`)
    } finally {
      setLoading(false)
    }
  }

  const suggestCrewSwap = async (data: CrewSwapForm) => {
    setLoading(true)
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_GATEWAY_URL || 'http://localhost:8080'}/crew/suggest_swap`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      })

      if (!res.ok) throw new Error('Failed to suggest crew swap')
      
      const result = await res.json()
      setSwapResults(prev => [result, ...prev])
      toast.success('Crew swap suggestions generated!')
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred'
      toast.error(`Failed to suggest crew swap: ${errorMessage}`)
    } finally {
      setLoading(false)
    }
  }

  const loadAvailableCrew = async (date: string, role?: string) => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ date })
      if (role) params.append('role', role)
      
      const res = await fetch(`${process.env.NEXT_PUBLIC_GATEWAY_URL || 'http://localhost:8080'}/crew/availability?${params}`)
      
      if (!res.ok) throw new Error('Failed to load available crew')
      
      const result = await res.json()
      setAvailableCrew(result.available_crew || [])
      toast.success(`Loaded ${result.total_available || 0} available crew members`)
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred'
      toast.error(`Failed to load crew: ${errorMessage}`)
    } finally {
      setLoading(false)
    }
  }

  const getRiskColor = (riskLevel: string) => {
    switch (riskLevel) {
      case 'high': return 'text-red-600 bg-red-100'
      case 'medium': return 'text-yellow-600 bg-yellow-100'
      case 'low': return 'text-green-600 bg-green-100'
      default: return 'text-gray-600 bg-gray-100'
    }
  }

  const getRiskIcon = (riskLevel: string) => {
    switch (riskLevel) {
      case 'high': return <XCircle className="h-4 w-4" />
      case 'medium': return <AlertTriangle className="h-4 w-4" />
      case 'low': return <CheckCircle className="h-4 w-4" />
      default: return <Clock className="h-4 w-4" />
    }
  }

  return (
    <div className="relative min-h-screen">
      {/* Background */}
      <div className="absolute inset-0 bg-gradient-to-br from-green-50 via-emerald-50 to-teal-50">
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-16 right-16 w-80 h-32 bg-gradient-to-r from-green-400 to-emerald-600 rounded-full transform rotate-12 opacity-20"></div>
          <div className="absolute top-32 right-8 w-64 h-24 bg-gradient-to-r from-teal-300 to-cyan-500 rounded-full transform rotate-6 opacity-15"></div>
          <div className="absolute top-48 right-24 w-48 h-16 bg-gradient-to-r from-emerald-400 to-green-600 rounded-full transform -rotate-3 opacity-10"></div>
        </div>
      </div>

      {/* Header */}
      <header className="bg-gradient-to-r from-green-900 to-emerald-900 text-white relative z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between py-6">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <div className="w-8 h-8 bg-white rounded-full flex items-center justify-center">
                  <Users className="h-5 w-5 text-green-900" />
                </div>
                <div>
                  <h1 className="text-2xl font-bold">Crew Management</h1>
                  <p className="text-sm text-green-200">AI-powered crew optimization</p>
                </div>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <Link href="/" className="text-sm font-medium text-white hover:text-green-200">
                Back to Home
              </Link>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 relative z-10">
        {/* Tab Navigation */}
        <div className="mb-8">
          <div className="border-b-2 border-gray-200">
            <nav className="-mb-px flex space-x-8">
              {[
                { id: 'optimize', label: 'Crew Optimization', icon: Wrench },
                { id: 'swap', label: 'Crew Swaps', icon: RefreshCw },
                { id: 'availability', label: 'Availability', icon: Search }
              ].map((tab) => {
                const Icon = tab.icon
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id as any)}
                    className={`flex items-center py-4 px-1 border-b-2 font-semibold text-sm transition-colors ${
                      activeTab === tab.id
                        ? 'border-green-600 text-green-600'
                        : 'border-transparent text-gray-600 hover:text-green-600 hover:border-gray-300'
                    }`}
                  >
                    <Icon className="h-5 w-5 mr-2" />
                    {tab.label}
                  </button>
                )
              })}
            </nav>
          </div>
        </div>

        {/* Crew Optimization Tab */}
        {activeTab === 'optimize' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Optimization Form */}
            <div className="bg-white/95 backdrop-blur-sm rounded-xl shadow-lg p-6 border-2 border-gray-200">
              <h2 className="text-xl font-bold text-gray-900 mb-6">Optimize Crew Assignments</h2>
              
              <form onSubmit={optimizationForm.handleSubmit(optimizeCrew)} className="space-y-5">
                <div>
                  <label className="block text-sm font-semibold text-gray-900 mb-2">
                    Flight Number
                  </label>
                  <input
                    {...optimizationForm.register('flight_no')}
                    className="w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-green-600 focus:border-transparent transition-colors"
                    placeholder="NZ123"
                  />
                </div>

                <div>
                  <label className="block text-sm font-semibold text-gray-900 mb-2">
                    Date
                  </label>
                  <input
                    {...optimizationForm.register('date')}
                    type="date"
                    className="w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-green-600 focus:border-transparent transition-colors"
                  />
                </div>

                <div>
                  <label className="block text-sm font-semibold text-gray-900 mb-2">
                    Disruption Type
                  </label>
                  <select
                    {...optimizationForm.register('disruption_type')}
                    className="w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-green-600 focus:border-transparent transition-colors"
                  >
                    <option value="weather_delay">Weather Delay</option>
                    <option value="crew_sickness">Crew Sickness</option>
                    <option value="aircraft_issue">Aircraft Issue</option>
                    <option value="operational_delay">Operational Delay</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-semibold text-gray-900 mb-2">
                    Time Constraint (hours)
                  </label>
                  <input
                    {...optimizationForm.register('time_constraint', { valueAsNumber: true })}
                    type="number"
                    min="1"
                    max="24"
                    className="w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-green-600 focus:border-transparent transition-colors"
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-green-600 text-white py-3 px-6 rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center font-semibold transition-colors"
                >
                  {loading ? (
                    <>
                      <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                      Optimizing...
                    </>
                  ) : (
                    <>
                      <Wrench className="h-5 w-5 mr-2" />
                      Optimize Crew
                    </>
                  )}
                </button>
              </form>
            </div>

            {/* Optimization Results */}
            <div className="lg:col-span-2 space-y-6">
              {optimizationResults.length === 0 ? (
                <div className="bg-white/95 backdrop-blur-sm rounded-xl shadow-lg p-8 border-2 border-gray-200 text-center">
                  <Users className="h-16 w-16 mx-auto mb-4 text-gray-400" />
                  <p className="text-xl font-bold text-gray-600">No optimizations yet</p>
                  <p className="text-sm text-gray-500 mt-2">Fill out the form to generate your first crew optimization</p>
                </div>
              ) : (
                optimizationResults.map((result, index) => (
                  <div key={index} className="bg-white/95 backdrop-blur-sm rounded-xl shadow-lg p-6 border-2 border-gray-200">
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center space-x-3">
                        <Plane className="h-6 w-6 text-green-600" />
                        <div>
                          <h3 className="text-lg font-bold text-gray-900">
                            {result.flight_no} - {result.date}
                          </h3>
                          <p className="text-sm text-gray-600">
                            Status: {result.optimization_status}
                          </p>
                        </div>
                      </div>
                      <div className={`px-3 py-1 rounded-full flex items-center space-x-2 ${getRiskColor(result.crew_analysis.risk_level)}`}>
                        {getRiskIcon(result.crew_analysis.risk_level)}
                        <span className="text-sm font-semibold capitalize">
                          {result.crew_analysis.risk_level} risk
                        </span>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                      <div className="bg-gray-50 rounded-lg p-3">
                        <div className="text-sm font-medium text-gray-600">Priority</div>
                        <div className="text-2xl font-bold text-gray-900">
                          {result.crew_analysis.priority}/5
                        </div>
                      </div>
                      <div className="bg-gray-50 rounded-lg p-3">
                        <div className="text-sm font-medium text-gray-600">Resolution Time</div>
                        <div className="text-lg font-bold text-gray-900">
                          {result.crew_analysis.estimated_resolution_time}
                        </div>
                      </div>
                    </div>

                    {/* Crew Members */}
                    <div className="mb-4">
                      <h4 className="text-sm font-semibold text-gray-900 mb-3">Crew Members</h4>
                      <div className="space-y-2">
                        {result.crew_members.map((member, memberIndex) => (
                          <div key={memberIndex} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                            <div className="flex items-center space-x-3">
                              <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
                                <UserCheck className="h-4 w-4 text-green-600" />
                              </div>
                              <div>
                                <div className="font-medium text-gray-900">{member.name}</div>
                                <div className="text-sm text-gray-600">{member.role} • {member.crew_id}</div>
                              </div>
                            </div>
                            <div className="flex items-center space-x-2">
                              {member.is_legal ? (
                                <CheckCircle className="h-5 w-5 text-green-500" />
                              ) : (
                                <XCircle className="h-5 w-5 text-red-500" />
                              )}
                              <span className="text-sm text-gray-600">
                                {member.duty_hours.toFixed(1)}h / {member.max_duty_hours}h
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Recommendations */}
                    {result.recommendations.length > 0 && (
                      <div>
                        <h4 className="text-sm font-semibold text-gray-900 mb-2">Recommendations</h4>
                        <ul className="space-y-1">
                          {result.recommendations.map((recommendation, recIndex) => (
                            <li key={recIndex} className="flex items-start space-x-2 text-sm text-gray-700">
                              <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
                              <span>{recommendation}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* Crew Swap Tab */}
        {activeTab === 'swap' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Swap Form */}
            <div className="bg-white/95 backdrop-blur-sm rounded-xl shadow-lg p-6 border-2 border-gray-200">
              <h2 className="text-xl font-bold text-gray-900 mb-6">Suggest Crew Swap</h2>
              
              <form onSubmit={swapForm.handleSubmit(suggestCrewSwap)} className="space-y-5">
                <div>
                  <label className="block text-sm font-semibold text-gray-900 mb-2">
                    Flight Number
                  </label>
                  <input
                    {...swapForm.register('flight_no')}
                    className="w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-green-600 focus:border-transparent transition-colors"
                    placeholder="NZ123"
                  />
                </div>

                <div>
                  <label className="block text-sm font-semibold text-gray-900 mb-2">
                    Date
                  </label>
                  <input
                    {...swapForm.register('date')}
                    type="date"
                    className="w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-green-600 focus:border-transparent transition-colors"
                  />
                </div>

                <div>
                  <label className="block text-sm font-semibold text-gray-900 mb-2">
                    Unavailable Crew ID
                  </label>
                  <input
                    {...swapForm.register('unavailable_crew_id')}
                    className="w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-green-600 focus:border-transparent transition-colors"
                    placeholder="CAP001"
                  />
                </div>

                <div>
                  <label className="block text-sm font-semibold text-gray-900 mb-2">
                    Reason
                  </label>
                  <select
                    {...swapForm.register('reason')}
                    className="w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-green-600 focus:border-transparent transition-colors"
                  >
                    <option value="illness">Illness</option>
                    <option value="fatigue">Fatigue</option>
                    <option value="personal">Personal Emergency</option>
                    <option value="duty_limit">Duty Time Limit</option>
                    <option value="other">Other</option>
                  </select>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-green-600 text-white py-3 px-6 rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center font-semibold transition-colors"
                >
                  {loading ? (
                    <>
                      <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                      Finding Swaps...
                    </>
                  ) : (
                    <>
                      <RefreshCw className="h-5 w-5 mr-2" />
                      Find Swaps
                    </>
                  )}
                </button>
              </form>
            </div>

            {/* Swap Results */}
            <div className="lg:col-span-2 space-y-6">
              {swapResults.length === 0 ? (
                <div className="bg-white/95 backdrop-blur-sm rounded-xl shadow-lg p-8 border-2 border-gray-200 text-center">
                  <RefreshCw className="h-16 w-16 mx-auto mb-4 text-gray-400" />
                  <p className="text-xl font-bold text-gray-600">No swap suggestions yet</p>
                  <p className="text-sm text-gray-500 mt-2">Fill out the form to find crew replacement options</p>
                </div>
              ) : (
                swapResults.map((result, index) => (
                  <div key={index} className="bg-white/95 backdrop-blur-sm rounded-xl shadow-lg p-6 border-2 border-gray-200">
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center space-x-3">
                        <Plane className="h-6 w-6 text-green-600" />
                        <div>
                          <h3 className="text-lg font-bold text-gray-900">
                            {result.flight_no} - {result.date}
                          </h3>
                          <p className="text-sm text-gray-600">
                            Replacing: {result.unavailable_crew}
                          </p>
                        </div>
                      </div>
                      <div className="text-sm text-gray-600">
                        {result.swap_suggestions.length} suggestions
                      </div>
                    </div>

                    {result.swap_suggestions.map((swap, swapIndex) => (
                      <div key={swapIndex} className="border border-gray-200 rounded-lg p-4 mb-4">
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center space-x-3">
                            <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                              <UserCheck className="h-4 w-4 text-blue-600" />
                            </div>
                            <div>
                              <div className="font-medium text-gray-900">{swap.replacement_crew.name}</div>
                              <div className="text-sm text-gray-600">{swap.replacement_crew.role} • {swap.replacement_crew.crew_id}</div>
                            </div>
                          </div>
                          <div className="flex items-center space-x-2">
                            {swap.legality_check ? (
                              <CheckCircle className="h-5 w-5 text-green-500" />
                            ) : (
                              <XCircle className="h-5 w-5 text-red-500" />
                            )}
                            <span className="text-sm text-gray-600">
                              ${swap.cost_impact}
                            </span>
                          </div>
                        </div>
                        
                        <div className="text-sm text-gray-600 mb-2">
                          <strong>Qualifications:</strong> {swap.replacement_crew.qualifications.join(', ')}
                        </div>
                        <div className="text-sm text-gray-600 mb-2">
                          <strong>Duty Hours:</strong> {swap.replacement_crew.duty_hours.toFixed(1)}h / {swap.replacement_crew.max_duty_hours}h
                        </div>
                        <div className="text-sm text-gray-600">
                          <strong>Implementation Time:</strong> {swap.implementation_time}
                        </div>
                      </div>
                    ))}
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* Availability Tab */}
        {activeTab === 'availability' && (
          <div className="space-y-6">
            <div className="bg-white/95 backdrop-blur-sm rounded-xl shadow-lg p-6 border-2 border-gray-200">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-bold text-gray-900">Crew Availability</h2>
                  <p className="text-sm text-gray-600 mt-1">
                    View available crew members for a specific date
                  </p>
                </div>
                <div className="flex space-x-3">
                  <input
                    type="date"
                    id="availability-date"
                    className="px-4 py-2 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-green-600 focus:border-transparent"
                    defaultValue="2025-09-17"
                  />
                  <select
                    id="availability-role"
                    className="px-4 py-2 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-green-600 focus:border-transparent"
                  >
                    <option value="">All Roles</option>
                    <option value="Captain">Captain</option>
                    <option value="First Officer">First Officer</option>
                    <option value="Cabin Crew">Cabin Crew</option>
                  </select>
                  <button
                    onClick={() => {
                      const date = (document.getElementById('availability-date') as HTMLInputElement)?.value
                      const role = (document.getElementById('availability-role') as HTMLSelectElement)?.value
                      if (date) loadAvailableCrew(date, role || undefined)
                    }}
                    disabled={loading}
                    className="bg-green-600 text-white py-2 px-4 rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center font-semibold transition-colors"
                  >
                    {loading ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Search className="h-4 w-4" />
                    )}
                  </button>
                </div>
              </div>
            </div>

            {availableCrew.length > 0 && (
              <div className="bg-white/95 backdrop-blur-sm rounded-xl shadow-lg border-2 border-gray-200">
                <div className="p-6 border-b-2 border-gray-200">
                  <h3 className="text-lg font-bold text-gray-900">
                    Available Crew Members
                  </h3>
                  <p className="text-sm text-gray-600">
                    {availableCrew.length} crew members available
                  </p>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Name
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Role
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Qualifications
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Duty Hours
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Status
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {availableCrew.map((member, index) => (
                        <tr key={index} className="hover:bg-gray-50">
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="flex items-center">
                              <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center mr-3">
                                <UserCheck className="h-4 w-4 text-green-600" />
                              </div>
                              <div>
                                <div className="text-sm font-medium text-gray-900">{member.name}</div>
                                <div className="text-sm text-gray-500">{member.crew_id}</div>
                              </div>
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            {member.role}
                          </td>
                          <td className="px-6 py-4 text-sm text-gray-600">
                            <div className="flex flex-wrap gap-1">
                              {member.qualifications.slice(0, 2).map((qual, qualIndex) => (
                                <span
                                  key={qualIndex}
                                  className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded"
                                >
                                  {qual}
                                </span>
                              ))}
                              {member.qualifications.length > 2 && (
                                <span className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded">
                                  +{member.qualifications.length - 2}
                                </span>
                              )}
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                            {member.duty_hours.toFixed(1)}h / {member.max_duty_hours}h
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span className={`px-2 py-1 rounded-full text-xs font-semibold flex items-center w-fit ${
                              member.availability_status === 'available' ? 'text-green-800 bg-green-100' : 'text-red-800 bg-red-100'
                            }`}>
                              {member.availability_status === 'available' ? (
                                <CheckCircle className="h-3 w-3 mr-1" />
                              ) : (
                                <XCircle className="h-3 w-3 mr-1" />
                              )}
                              {member.availability_status === 'available' ? 'Available' : 'Unavailable'}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
