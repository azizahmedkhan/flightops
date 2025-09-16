'use client'

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'react-hot-toast'
import { 
  Plane, 
  Calendar, 
  Search, 
  Loader2, 
  AlertCircle,
  CheckCircle,
  Clock,
  Users,
  DollarSign
} from 'lucide-react'

const querySchema = z.object({
  question: z.string().min(1, 'Question is required'),
  flight_no: z.string().min(1, 'Flight number is required'),
  date: z.string().min(1, 'Date is required')
})

type QueryForm = z.infer<typeof querySchema>

interface QueryResponse {
  answer: {
    issue: string
    impact_summary: string
    options_summary: string
    citations: string[]
  }
  tools_payload: {
    flight: {
      flight_no: string
      origin: string
      destination: string
      sched_dep: string
      sched_arr: string
      status: string
    }
    impact: {
      passengers: number
      crew: number
      summary: string
    }
    options: Array<{
      plan: string
      cx_score: number
      cost_estimate: number
      notes: string
    }>
    policy_citations: string[]
  }
}

export default function QueryPage() {
  const [response, setResponse] = useState<QueryResponse | null>(null)
  const [loading, setLoading] = useState(false)

  const { register, handleSubmit, formState: { errors }, watch } = useForm<QueryForm>({
    resolver: zodResolver(querySchema),
    defaultValues: {
      question: 'What is the impact of the delay on NZ123 today?',
      flight_no: 'NZ123',
      date: '2025-09-17'
    }
  })

  const onSubmit = async (data: QueryForm) => {
    setLoading(true)
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_GATEWAY_URL || 'http://localhost:8080'}/ask`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
      })

      if (!res.ok) {
        throw new Error('Failed to get response')
      }

      const result = await res.json()
      setResponse(result)
      toast.success('Query processed successfully!')
    } catch (error) {
      toast.error('Failed to process query. Please try again.')
      console.error('Query error:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between py-6">
            <div className="flex items-center space-x-3">
              <Plane className="h-8 w-8 text-blue-600" />
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Flight Query</h1>
                <p className="text-sm text-gray-600">Ask questions about flight disruptions</p>
              </div>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Query Form */}
          <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900 mb-6">Ask a Question</h2>
            
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Question
                </label>
                <textarea
                  {...register('question')}
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="What is the impact of the delay on NZ123 today?"
                />
                {errors.question && (
                  <p className="mt-1 text-sm text-red-600">{errors.question.message}</p>
                )}
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Flight Number
                  </label>
                  <input
                    {...register('flight_no')}
                    type="text"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="NZ123"
                  />
                  {errors.flight_no && (
                    <p className="mt-1 text-sm text-red-600">{errors.flight_no.message}</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Date
                  </label>
                  <input
                    {...register('date')}
                    type="date"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                  {errors.date && (
                    <p className="mt-1 text-sm text-red-600">{errors.date.message}</p>
                  )}
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Processing...
                  </>
                ) : (
                  <>
                    <Search className="h-4 w-4 mr-2" />
                    Ask Question
                  </>
                )}
              </button>
            </form>
          </div>

          {/* Response */}
          <div className="space-y-6">
            {response && (
              <>
                {/* Flight Information */}
                <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                    <Plane className="h-5 w-5 mr-2 text-blue-600" />
                    Flight Information
                  </h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm text-gray-600">Flight</p>
                      <p className="font-medium">{response.tools_payload.flight.flight_no}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600">Status</p>
                      <p className="font-medium">{response.tools_payload.flight.status}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600">Route</p>
                      <p className="font-medium">
                        {response.tools_payload.flight.origin} → {response.tools_payload.flight.destination}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600">Schedule</p>
                      <p className="font-medium">
                        {response.tools_payload.flight.sched_dep} - {response.tools_payload.flight.sched_arr}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Impact Assessment */}
                <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                    <Users className="h-5 w-5 mr-2 text-orange-600" />
                    Impact Assessment
                  </h3>
                  <div className="grid grid-cols-2 gap-4 mb-4">
                    <div className="text-center p-4 bg-orange-50 rounded-lg">
                      <p className="text-2xl font-bold text-orange-600">
                        {response.tools_payload.impact.passengers}
                      </p>
                      <p className="text-sm text-orange-600">Passengers</p>
                    </div>
                    <div className="text-center p-4 bg-blue-50 rounded-lg">
                      <p className="text-2xl font-bold text-blue-600">
                        {response.tools_payload.impact.crew}
                      </p>
                      <p className="text-sm text-blue-600">Crew Members</p>
                    </div>
                  </div>
                  <p className="text-sm text-gray-600">{response.tools_payload.impact.summary}</p>
                </div>

                {/* Rebooking Options */}
                <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                    <DollarSign className="h-5 w-5 mr-2 text-green-600" />
                    Rebooking Options
                  </h3>
                  <div className="space-y-3">
                    {response.tools_payload.options.map((option, index) => (
                      <div key={index} className="p-4 border border-gray-200 rounded-lg">
                        <div className="flex justify-between items-start mb-2">
                          <p className="font-medium text-gray-900">{option.plan}</p>
                          <div className="flex items-center space-x-2">
                            <span className="text-sm text-gray-600">
                              CX: {(option.cx_score * 100).toFixed(0)}%
                            </span>
                            <span className="text-sm text-gray-600">
                              Cost: ${option.cost_estimate.toLocaleString()}
                            </span>
                          </div>
                        </div>
                        <p className="text-sm text-gray-600">{option.notes}</p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Policy Citations */}
                {response.answer.citations.length > 0 && (
                  <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
                    <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                      <CheckCircle className="h-5 w-5 mr-2 text-green-600" />
                      Policy Citations
                    </h3>
                    <div className="space-y-2">
                      {response.answer.citations.map((citation, index) => (
                        <div key={index} className="p-3 bg-green-50 rounded-lg">
                          <p className="text-sm text-gray-700">{citation}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}

            {!response && (
              <div className="bg-white rounded-xl shadow-sm p-12 border border-gray-200 text-center">
                <Search className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-500">Submit a query to see results here</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
