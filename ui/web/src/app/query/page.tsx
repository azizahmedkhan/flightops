'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
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
  DollarSign,
  X
} from 'lucide-react'
import QuestionSelector from '../components/QuestionSelector'
import FlightNumberInput from '../components/FlightNumberInput'

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

  const { register, handleSubmit, formState: { errors }, watch, setValue } = useForm<QueryForm>({
    resolver: zodResolver(querySchema),
    defaultValues: {
      question: '',
      flight_no: '',
      date: ''
    }
  })

  // Load saved state from localStorage on component mount
  useEffect(() => {
    const savedResponse = localStorage.getItem('agent-query-response')
    const savedFormData = localStorage.getItem('agent-query-form')
    
    if (savedResponse) {
      try {
        setResponse(JSON.parse(savedResponse))
      } catch (error) {
        console.error('Failed to parse saved response:', error)
        localStorage.removeItem('agent-query-response')
      }
    }
    
    if (savedFormData) {
      try {
        const formData = JSON.parse(savedFormData)
        setValue('question', formData.question || '')
        setValue('flight_no', formData.flight_no || '')
        setValue('date', formData.date || '')
      } catch (error) {
        console.error('Failed to parse saved form data:', error)
        localStorage.removeItem('agent-query-form')
      }
    }
  }, [setValue])

  const onSubmit = async (data: QueryForm) => {
    setLoading(true)
    try {
      // Save form data to localStorage
      localStorage.setItem('agent-query-form', JSON.stringify(data))
      
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
      
      // Dispatch custom event if LLM message is present
      if (result.llm_message) {
        const event = new CustomEvent('llm-message', { detail: result.llm_message })
        window.dispatchEvent(event)
      }
      
      // Save response to localStorage
      localStorage.setItem('agent-query-response', JSON.stringify(result))
      
      toast.success('Query processed successfully!')
    } catch (error) {
      toast.error('Failed to process query. Please try again.')
      console.error('Query error:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleQuestionSelect = (question: string) => {
    setValue('question', question)
  }

  const handleFlightSelect = (suggestion: any) => {
    setValue('flight_no', suggestion.flight_no)
    setValue('date', suggestion.flight_date)
  }

  // Save form data to localStorage whenever it changes
  const watchedValues = watch()
  useEffect(() => {
    if (watchedValues.question || watchedValues.flight_no || watchedValues.date) {
      localStorage.setItem('agent-query-form', JSON.stringify(watchedValues))
    }
  }, [watchedValues])

  // Clear all saved state
  const clearState = () => {
    setResponse(null)
    setValue('question', '')
    setValue('flight_no', '')
    setValue('date', '')
    localStorage.removeItem('agent-query-response')
    localStorage.removeItem('agent-query-form')
    toast.success('Query state cleared!')
  }

  return (
    <div className="min-h-screen relative">
      {/* Header */}
      <header className="bg-black text-white relative z-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between py-6">
            <div className="flex items-center space-x-3">
              <div className="bg-white p-2 rounded-lg">
                <Plane className="h-6 w-6 text-black" />
              </div>
              <div>
                <h1 className="text-2xl font-bold">Flight Query</h1>
                <p className="text-sm text-gray-300">Ask questions about flight disruptions</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              {(response || watchedValues.question || watchedValues.flight_no || watchedValues.date) && (
                <button
                  onClick={clearState}
                  className="text-sm font-medium text-white hover:text-gray-200 flex items-center space-x-1"
                  title="Clear query and results"
                >
                  <X className="h-4 w-4" />
                  <span>Clear</span>
                </button>
              )}
              <Link href="/" className="text-sm font-medium text-white hover:text-gray-200">
                Back to Home
              </Link>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 relative z-10">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Query Form */}
          <div className="bg-white/95 backdrop-blur-sm rounded-xl shadow-lg p-6 border-2 border-gray-200">
            <h2 className="text-xl font-bold text-black mb-6">Ask a Question</h2>
            
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
              <div>
                <label className="block text-sm font-semibold text-gray-900 mb-2">
                  Question
                </label>
                <QuestionSelector
                  onQuestionSelect={handleQuestionSelect}
                  flightNo={watchedValues.flight_no || ''}
                  date={watchedValues.date || ''}
                />
                <textarea
                  {...register('question')}
                  rows={3}
                  className="w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-black focus:border-transparent transition-colors mt-2"
                  placeholder="Enter your question or select from common questions above..."
                />
                {errors.question && (
                  <p className="mt-1 text-sm text-red-600 font-medium">{errors.question.message}</p>
                )}
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-semibold text-gray-900 mb-2">
                    Flight Number
                  </label>
                  <FlightNumberInput
                    value={watchedValues.flight_no || ''}
                    onChange={(value) => setValue('flight_no', value)}
                    onSelect={handleFlightSelect}
                    error={errors.flight_no?.message}
                  />
                </div>

                <div>
                  <label className="block text-sm font-semibold text-gray-900 mb-2">
                    Date
                  </label>
                  <input
                    {...register('date')}
                    type="date"
                    className="w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-black focus:border-transparent transition-colors"
                  />
                  {errors.date && (
                    <p className="mt-1 text-sm text-red-600 font-medium">{errors.date.message}</p>
                  )}
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-black text-white py-3 px-6 rounded-lg hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center font-semibold transition-colors"
              >
                {loading ? (
                  <>
                    <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                    Processing...
                  </>
                ) : (
                  <>
                    <Search className="h-5 w-5 mr-2" />
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
                <div className="bg-white/95 backdrop-blur-sm rounded-xl shadow-lg p-6 border-2 border-gray-200">
                  <h3 className="text-xl font-bold text-black mb-4 flex items-center">
                    <div className="bg-black p-2 rounded-lg mr-3">
                      <Plane className="h-5 w-5 text-white" />
                    </div>
                    Flight Information
                  </h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm text-gray-600 font-semibold">Flight</p>
                      <p className="font-bold text-black">{response.tools_payload?.flight?.flight_no}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600 font-semibold">Status</p>
                      <p className="font-bold text-black">{response.tools_payload?.flight?.status}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600 font-semibold">Route</p>
                      <p className="font-bold text-black">
                        {response.tools_payload?.flight?.origin} → {response.tools_payload?.flight?.destination}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600 font-semibold">Schedule</p>
                      <p className="font-bold text-black">
                        {response.tools_payload?.flight?.sched_dep} - {response.tools_payload?.flight?.sched_arr}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Impact Assessment */}
                <div className="bg-white/95 backdrop-blur-sm rounded-xl shadow-lg p-6 border-2 border-gray-200">
                  <h3 className="text-xl font-bold text-black mb-4 flex items-center">
                    <div className="bg-black p-2 rounded-lg mr-3">
                      <Users className="h-5 w-5 text-white" />
                    </div>
                    Impact Assessment
                  </h3>
                  <div className="grid grid-cols-2 gap-4 mb-4">
                    <div className="text-center p-4 bg-gray-100 rounded-lg border-2 border-gray-200">
                      <p className="text-2xl font-bold text-black">
                        {response.tools_payload?.impact?.passengers}
                      </p>
                      <p className="text-sm text-gray-600 font-semibold">Passengers</p>
                    </div>
                    <div className="text-center p-4 bg-gray-100 rounded-lg border-2 border-gray-200">
                      <p className="text-2xl font-bold text-black">
                        {response.tools_payload?.impact?.crew}
                      </p>
                      <p className="text-sm text-gray-600 font-semibold">Crew Members</p>
                    </div>
                  </div>
                  <p className="text-sm text-gray-800 font-medium">{response.tools_payload?.impact?.summary}</p>
                </div>

                {/* Rebooking Options */}
                <div className="bg-white/95 backdrop-blur-sm rounded-xl shadow-lg p-6 border-2 border-gray-200">
                  <h3 className="text-xl font-bold text-black mb-4 flex items-center">
                    <div className="bg-black p-2 rounded-lg mr-3">
                      <DollarSign className="h-5 w-5 text-white" />
                    </div>
                    Rebooking Options
                  </h3>
                  <div className="space-y-3">
                    {response.tools_payload?.options?.map((option, index) => (
                      <div key={index} className="p-4 border-2 border-gray-200 rounded-lg bg-gray-50">
                        <div className="flex justify-between items-start mb-2">
                          <p className="font-bold text-black">{option.plan}</p>
                          <div className="flex items-center space-x-2">
                            <span className="text-sm text-black font-semibold">
                              CX: {(option.cx_score * 100).toFixed(0)}%
                            </span>
                            <span className="text-sm text-gray-600 font-semibold">
                              Cost: ${option.cost_estimate.toLocaleString()}
                            </span>
                          </div>
                        </div>
                        <p className="text-sm text-gray-700 font-medium">{option.notes}</p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Policy Citations */}
                {response.answer?.citations?.length > 0 && (
                  <div className="bg-white/95 backdrop-blur-sm rounded-xl shadow-lg p-6 border-2 border-gray-200">
                    <h3 className="text-xl font-bold text-black mb-4 flex items-center">
                      <div className="bg-black p-2 rounded-lg mr-3">
                        <CheckCircle className="h-5 w-5 text-white" />
                      </div>
                      Policy Citations
                    </h3>
                    <div className="space-y-2">
                      {response.answer?.citations?.map((citation, index) => (
                        <div key={index} className="p-3 bg-gray-100 rounded-lg border-2 border-gray-200">
                          <p className="text-sm text-gray-800 font-medium">{citation}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}

            {!response && (
              <div className="bg-white/95 backdrop-blur-sm rounded-xl shadow-lg p-12 border-2 border-gray-200 text-center">
                <div className="bg-black p-4 rounded-full w-16 h-16 mx-auto mb-4 flex items-center justify-center">
                  <Search className="h-8 w-8 text-white" />
                </div>
                <p className="text-gray-600 font-semibold">Submit a query to see results here</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
