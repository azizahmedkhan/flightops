'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'react-hot-toast'
import { 
  TrendingUp, 
  AlertTriangle, 
  Clock, 
  Plane, 
  Users, 
  Wrench,
  CheckCircle,
  XCircle,
  Loader2,
  BarChart3,
  Target,
  Zap
} from 'lucide-react'
import FlightNumberInput from '../components/FlightNumberInput'

const predictionSchema = z.object({
  flight_no: z.string().min(1, 'Flight number is required'),
  date: z.string().min(1, 'Date is required'),
  hours_ahead: z.number().min(1).max(24).default(4),
  include_weather: z.boolean().default(true),
  include_crew: z.boolean().default(true),
  include_aircraft: z.boolean().default(true)
})

type PredictionForm = z.infer<typeof predictionSchema>

interface DisruptionPrediction {
  flight_no: string
  date: string
  risk_level: string
  risk_score: number
  predicted_disruption_type: string
  confidence: number
  factors: string[]
  recommendations: string[]
  time_to_disruption?: string
}

interface PredictionResult {
  prediction: DisruptionPrediction
  analysis_data: {
    weather: any
    crew: any
    aircraft: any
    historical: any
  }
}

export default function PredictivePage() {
  const [predictions, setPredictions] = useState<PredictionResult[]>([])
  const [bulkPredictions, setBulkPredictions] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<'single' | 'bulk'>('single')

  const form = useForm<PredictionForm>({
    resolver: zodResolver(predictionSchema),
    defaultValues: {
      flight_no: '',
      date: '',
      hours_ahead: 4,
      include_weather: true,
      include_crew: true,
      include_aircraft: true
    }
  })

  const handleFlightSelect = (suggestion: any) => {
    form.setValue('flight_no', suggestion.flight_no)
    form.setValue('date', suggestion.flight_date)
  }

  const predictDisruption = async (data: PredictionForm) => {
    setLoading(true)
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_GATEWAY_URL || 'http://localhost:8080'}/predict/disruptions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      })

      if (!res.ok) throw new Error('Failed to predict disruption')
      
      const result = await res.json()
      setPredictions(prev => [result, ...prev])
      toast.success('Prediction generated successfully!')
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred'
      toast.error(`Failed to predict disruption: ${errorMessage}`)
    } finally {
      setLoading(false)
    }
  }

  const predictBulkDisruptions = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_GATEWAY_URL || 'http://localhost:8080'}/predict/bulk`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })

      if (!res.ok) throw new Error('Failed to predict bulk disruptions')
      
      const result = await res.json()
      setBulkPredictions(result.predictions || [])
      toast.success(`Generated ${result.predictions?.length || 0} predictions!`)
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred'
      toast.error(`Failed to predict bulk disruptions: ${errorMessage}`)
    } finally {
      setLoading(false)
    }
  }

  const getRiskColor = (riskLevel: string) => {
    switch (riskLevel) {
      case 'critical': return 'text-red-600 bg-red-100'
      case 'high': return 'text-orange-600 bg-orange-100'
      case 'medium': return 'text-yellow-600 bg-yellow-100'
      case 'low': return 'text-green-600 bg-green-100'
      default: return 'text-gray-600 bg-gray-100'
    }
  }

  const getRiskIcon = (riskLevel: string) => {
    switch (riskLevel) {
      case 'critical': return <XCircle className="h-5 w-5" />
      case 'high': return <AlertTriangle className="h-5 w-5" />
      case 'medium': return <Clock className="h-5 w-5" />
      case 'low': return <CheckCircle className="h-5 w-5" />
      default: return <Clock className="h-5 w-5" />
    }
  }

  return (
    <div className="relative min-h-screen">
      {/* Background */}
      <div className="absolute inset-0 bg-gradient-to-br from-blue-50 via-indigo-50 to-gray-50">
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-16 right-16 w-80 h-32 bg-gradient-to-r from-blue-400 to-indigo-600 rounded-full transform rotate-12 opacity-20"></div>
          <div className="absolute top-32 right-8 w-64 h-24 bg-gradient-to-r from-gray-300 to-pink-500 rounded-full transform rotate-6 opacity-15"></div>
          <div className="absolute top-48 right-24 w-48 h-16 bg-gradient-to-r from-indigo-400 to-blue-600 rounded-full transform -rotate-3 opacity-10"></div>
        </div>
      </div>

      {/* Header */}
      <header className="bg-gradient-to-r from-blue-900 to-indigo-900 text-white relative z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between py-6">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <div className="w-8 h-8 bg-white rounded-full flex items-center justify-center">
                  <TrendingUp className="h-5 w-5 text-blue-900" />
                </div>
                <div>
                  <h1 className="text-2xl font-bold">Predictive Analytics</h1>
                  <p className="text-sm text-blue-200">AI-powered disruption prediction</p>
                </div>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <Link href="/" className="text-sm font-medium text-white hover:text-blue-200">
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
                { id: 'single', label: 'Single Flight Prediction', icon: Target },
                { id: 'bulk', label: 'Bulk Predictions', icon: BarChart3 }
              ].map((tab) => {
                const Icon = tab.icon
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id as any)}
                    className={`flex items-center py-4 px-1 border-b-2 font-semibold text-sm transition-colors ${
                      activeTab === tab.id
                        ? 'border-blue-600 text-blue-600'
                        : 'border-transparent text-gray-600 hover:text-blue-600 hover:border-gray-300'
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

        {/* Single Flight Prediction Tab */}
        {activeTab === 'single' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Prediction Form */}
            <div className="bg-white/95 backdrop-blur-sm rounded-xl shadow-lg p-6 border-2 border-gray-200">
              <h2 className="text-xl font-bold text-gray-900 mb-6">Predict Flight Disruption</h2>
              
              <form onSubmit={form.handleSubmit(predictDisruption)} className="space-y-5">
                <div>
                  <label className="block text-sm font-semibold text-gray-900 mb-2">
                    Flight Number
                  </label>
                  <FlightNumberInput
                    value={form.watch('flight_no') || ''}
                    onChange={(value) => form.setValue('flight_no', value)}
                    onSelect={handleFlightSelect}
                    error={form.formState.errors.flight_no?.message}
                    className="focus:ring-blue-600"
                  />
                  {form.formState.errors.flight_no && (
                    <p className="mt-1 text-sm text-red-600 font-medium">
                      {form.formState.errors.flight_no.message}
                    </p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-semibold text-gray-900 mb-2">
                    Date
                  </label>
                  <input
                    {...form.register('date')}
                    type="date"
                    className="w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent transition-colors"
                  />
                  {form.formState.errors.date && (
                    <p className="mt-1 text-sm text-red-600 font-medium">
                      {form.formState.errors.date.message}
                    </p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-semibold text-gray-900 mb-2">
                    Hours Ahead
                  </label>
                  <input
                    {...form.register('hours_ahead', { valueAsNumber: true })}
                    type="number"
                    min="1"
                    max="24"
                    className="w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent transition-colors"
                  />
                </div>

                <div className="space-y-3">
                  <h3 className="text-sm font-semibold text-gray-900">Analysis Options</h3>
                  
                  <label className="flex items-center space-x-3">
                    <input
                      {...form.register('include_weather')}
                      type="checkbox"
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <span className="text-sm font-medium text-gray-700">Include Weather Analysis</span>
                  </label>

                  <label className="flex items-center space-x-3">
                    <input
                      {...form.register('include_crew')}
                      type="checkbox"
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <span className="text-sm font-medium text-gray-700">Include Crew Analysis</span>
                  </label>

                  <label className="flex items-center space-x-3">
                    <input
                      {...form.register('include_aircraft')}
                      type="checkbox"
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <span className="text-sm font-medium text-gray-700">Include Aircraft Analysis</span>
                  </label>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-blue-600 text-white py-3 px-6 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center font-semibold transition-colors"
                >
                  {loading ? (
                    <>
                      <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                      Predicting...
                    </>
                  ) : (
                    <>
                      <Zap className="h-5 w-5 mr-2" />
                      Predict Disruption
                    </>
                  )}
                </button>
              </form>
            </div>

            {/* Prediction Results */}
            <div className="lg:col-span-2 space-y-6">
              {predictions.length === 0 ? (
                <div className="bg-white/95 backdrop-blur-sm rounded-xl shadow-lg p-8 border-2 border-gray-200 text-center">
                  <TrendingUp className="h-16 w-16 mx-auto mb-4 text-gray-400" />
                  <p className="text-xl font-bold text-gray-600">No predictions yet</p>
                  <p className="text-sm text-gray-500 mt-2">Fill out the form to generate your first prediction</p>
                </div>
              ) : (
                predictions.map((result, index) => (
                  <div key={index} className="bg-white/95 backdrop-blur-sm rounded-xl shadow-lg p-6 border-2 border-gray-200">
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center space-x-3">
                        <Plane className="h-6 w-6 text-blue-600" />
                        <div>
                          <h3 className="text-lg font-bold text-gray-900">
                            {result.prediction.flight_no} - {result.prediction.date}
                          </h3>
                          <p className="text-sm text-gray-600">
                            {result.prediction.predicted_disruption_type}
                          </p>
                        </div>
                      </div>
                      <div className={`px-3 py-1 rounded-full flex items-center space-x-2 ${getRiskColor(result.prediction.risk_level)}`}>
                        {getRiskIcon(result.prediction.risk_level)}
                        <span className="text-sm font-semibold capitalize">
                          {result.prediction.risk_level}
                        </span>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                      <div className="bg-gray-50 rounded-lg p-3">
                        <div className="text-sm font-medium text-gray-600">Risk Score</div>
                        <div className="text-2xl font-bold text-gray-900">
                          {(result.prediction.risk_score * 100).toFixed(0)}%
                        </div>
                      </div>
                      <div className="bg-gray-50 rounded-lg p-3">
                        <div className="text-sm font-medium text-gray-600">Confidence</div>
                        <div className="text-2xl font-bold text-gray-900">
                          {(result.prediction.confidence * 100).toFixed(0)}%
                        </div>
                      </div>
                      <div className="bg-gray-50 rounded-lg p-3">
                        <div className="text-sm font-medium text-gray-600">Time to Disruption</div>
                        <div className="text-lg font-bold text-gray-900">
                          {result.prediction.time_to_disruption || 'N/A'}
                        </div>
                      </div>
                    </div>

                    {result.prediction.factors.length > 0 && (
                      <div className="mb-4">
                        <h4 className="text-sm font-semibold text-gray-900 mb-2">Risk Factors</h4>
                        <div className="flex flex-wrap gap-2">
                          {result.prediction.factors.map((factor, factorIndex) => (
                            <span
                              key={factorIndex}
                              className="px-2 py-1 bg-red-100 text-red-800 text-xs rounded-full"
                            >
                              {factor}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {result.prediction.recommendations.length > 0 && (
                      <div>
                        <h4 className="text-sm font-semibold text-gray-900 mb-2">Recommendations</h4>
                        <ul className="space-y-1">
                          {result.prediction.recommendations.map((recommendation, recIndex) => (
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

        {/* Bulk Predictions Tab */}
        {activeTab === 'bulk' && (
          <div className="space-y-6">
            <div className="bg-white/95 backdrop-blur-sm rounded-xl shadow-lg p-6 border-2 border-gray-200">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-bold text-gray-900">Bulk Disruption Predictions</h2>
                  <p className="text-sm text-gray-600 mt-1">
                    Predict disruptions for all flights in the next 24 hours
                  </p>
                </div>
                <button
                  onClick={predictBulkDisruptions}
                  disabled={loading}
                  className="bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center font-semibold transition-colors"
                >
                  {loading ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Predicting...
                    </>
                  ) : (
                    <>
                      <BarChart3 className="h-4 w-4 mr-2" />
                      Generate Predictions
                    </>
                  )}
                </button>
              </div>
            </div>

            {bulkPredictions.length > 0 && (
              <div className="bg-white/95 backdrop-blur-sm rounded-xl shadow-lg border-2 border-gray-200">
                <div className="p-6 border-b-2 border-gray-200">
                  <h3 className="text-lg font-bold text-gray-900">
                    Predictions for {bulkPredictions[0]?.date || 'Tomorrow'}
                  </h3>
                  <p className="text-sm text-gray-600">
                    {bulkPredictions.length} flights analyzed
                  </p>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Flight
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Route
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Departure
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Risk Level
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Risk Score
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Factors
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {bulkPredictions.map((prediction, index) => (
                        <tr key={index} className="hover:bg-gray-50">
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                            {prediction.flight_no}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                            {prediction.route}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                            {prediction.departure_time}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span className={`px-2 py-1 rounded-full text-xs font-semibold flex items-center w-fit ${getRiskColor(prediction.risk_level)}`}>
                              {getRiskIcon(prediction.risk_level)}
                              <span className="ml-1 capitalize">{prediction.risk_level}</span>
                            </span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                            {(prediction.risk_score * 100).toFixed(0)}%
                          </td>
                          <td className="px-6 py-4 text-sm text-gray-600">
                            <div className="flex flex-wrap gap-1">
                              {prediction.factors.slice(0, 2).map((factor: string, factorIndex: number) => (
                                <span
                                  key={factorIndex}
                                  className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded"
                                >
                                  {factor}
                                </span>
                              ))}
                              {prediction.factors.length > 2 && (
                                <span className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded">
                                  +{prediction.factors.length - 2} more
                                </span>
                              )}
                            </div>
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
