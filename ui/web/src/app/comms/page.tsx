'use client'

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'react-hot-toast'
import { 
  MessageSquare, 
  Plane, 
  Calendar, 
  Send, 
  Loader2,
  Mail,
  Smartphone,
  Copy,
  CheckCircle,
  AlertCircle
} from 'lucide-react'

const commsSchema = z.object({
  flight_no: z.string().min(1, 'Flight number is required'),
  date: z.string().min(1, 'Date is required'),
  tone: z.enum(['empathetic', 'professional', 'urgent']),
  channel: z.enum(['email', 'sms', 'both'])
})

type CommsForm = z.infer<typeof commsSchema>

interface CommsResponse {
  context: {
    flight_no: string
    date: string
    issue: string
    impact_summary: string
    options_summary: string
    policy_citations: string[]
  }
  draft: string
}

export default function CommsPage() {
  const [response, setResponse] = useState<CommsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [copied, setCopied] = useState(false)

  const { register, handleSubmit, formState: { errors }, watch } = useForm<CommsForm>({
    resolver: zodResolver(commsSchema),
    defaultValues: {
      flight_no: 'NZ123',
      date: '2025-09-17',
      tone: 'empathetic',
      channel: 'email'
    }
  })

  const onSubmit = async (data: CommsForm) => {
    setLoading(true)
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_GATEWAY_URL || 'http://localhost:8080'}/draft_comms`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: 'Draft email and sms',
          flight_no: data.flight_no,
          date: data.date
        })
      })

      if (!res.ok) {
        throw new Error('Failed to generate communication')
      }

      const result = await res.json()
      setResponse(result)
      toast.success('Communication drafted successfully!')
    } catch (error) {
      toast.error('Failed to draft communication. Please try again.')
      console.error('Comms error:', error)
    } finally {
      setLoading(false)
    }
  }

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      toast.success('Copied to clipboard!')
      setTimeout(() => setCopied(false), 2000)
    } catch (error) {
      toast.error('Failed to copy to clipboard')
    }
  }

  const toneOptions = [
    { value: 'empathetic', label: 'Empathetic', description: 'Warm and understanding tone' },
    { value: 'professional', label: 'Professional', description: 'Formal and business-like' },
    { value: 'urgent', label: 'Urgent', description: 'Direct and time-sensitive' }
  ]

  const channelOptions = [
    { value: 'email', label: 'Email', icon: Mail },
    { value: 'sms', label: 'SMS', icon: Smartphone },
    { value: 'both', label: 'Both', icon: MessageSquare }
  ]

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between py-6">
            <div className="flex items-center space-x-3">
              <MessageSquare className="h-8 w-8 text-green-600" />
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Draft Communications</h1>
                <p className="text-sm text-gray-600">Generate customer communications with policy grounding</p>
              </div>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Form */}
          <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900 mb-6">Communication Settings</h2>
            
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Flight Number
                  </label>
                  <input
                    {...register('flight_no')}
                    type="text"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
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
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                  />
                  {errors.date && (
                    <p className="mt-1 text-sm text-red-600">{errors.date.message}</p>
                  )}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Communication Tone
                </label>
                <div className="grid grid-cols-1 gap-3">
                  {toneOptions.map((option) => (
                    <label key={option.value} className="relative">
                      <input
                        {...register('tone')}
                        type="radio"
                        value={option.value}
                        className="sr-only"
                      />
                      <div className={`p-3 border rounded-lg cursor-pointer transition-all ${
                        watch('tone') === option.value
                          ? 'border-green-500 bg-green-50'
                          : 'border-gray-300 hover:border-gray-400'
                      }`}>
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="font-medium text-gray-900">{option.label}</p>
                            <p className="text-sm text-gray-600">{option.description}</p>
                          </div>
                          {watch('tone') === option.value && (
                            <CheckCircle className="h-5 w-5 text-green-600" />
                          )}
                        </div>
                      </div>
                    </label>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Communication Channel
                </label>
                <div className="grid grid-cols-3 gap-3">
                  {channelOptions.map((option) => {
                    const Icon = option.icon
                    return (
                      <label key={option.value} className="relative">
                        <input
                          {...register('channel')}
                          type="radio"
                          value={option.value}
                          className="sr-only"
                        />
                        <div className={`p-3 border rounded-lg cursor-pointer transition-all text-center ${
                          watch('channel') === option.value
                            ? 'border-green-500 bg-green-50'
                            : 'border-gray-300 hover:border-gray-400'
                        }`}>
                          <Icon className="h-6 w-6 mx-auto mb-2 text-gray-600" />
                          <p className="text-sm font-medium text-gray-900">{option.label}</p>
                        </div>
                      </label>
                    )
                  })}
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-green-600 text-white py-2 px-4 rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Drafting...
                  </>
                ) : (
                  <>
                    <Send className="h-4 w-4 mr-2" />
                    Draft Communication
                  </>
                )}
              </button>
            </form>
          </div>

          {/* Response */}
          <div className="space-y-6">
            {response && (
              <>
                {/* Context Information */}
                <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                    <Plane className="h-5 w-5 mr-2 text-blue-600" />
                    Flight Context
                  </h3>
                  <div className="space-y-3">
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-600">Flight:</span>
                      <span className="font-medium">{response.context.flight_no}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-600">Date:</span>
                      <span className="font-medium">{response.context.date}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-600">Issue:</span>
                      <span className="font-medium">{response.context.issue}</span>
                    </div>
                    <div>
                      <span className="text-sm text-gray-600">Impact:</span>
                      <p className="text-sm text-gray-900 mt-1">{response.context.impact_summary}</p>
                    </div>
                    <div>
                      <span className="text-sm text-gray-600">Options:</span>
                      <p className="text-sm text-gray-900 mt-1">{response.context.options_summary}</p>
                    </div>
                  </div>
                </div>

                {/* Draft Communication */}
                <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                      <MessageSquare className="h-5 w-5 mr-2 text-green-600" />
                      Draft Communication
                    </h3>
                    <button
                      onClick={() => copyToClipboard(response.draft)}
                      className="flex items-center px-3 py-1 text-sm text-gray-600 hover:text-gray-900 border border-gray-300 rounded-lg hover:bg-gray-50"
                    >
                      {copied ? (
                        <>
                          <CheckCircle className="h-4 w-4 mr-1" />
                          Copied!
                        </>
                      ) : (
                        <>
                          <Copy className="h-4 w-4 mr-1" />
                          Copy
                        </>
                      )}
                    </button>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <pre className="whitespace-pre-wrap text-sm text-gray-800 font-mono">
                      {response.draft}
                    </pre>
                  </div>
                </div>

                {/* Policy Citations */}
                {response.context.policy_citations.length > 0 && (
                  <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
                    <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                      <AlertCircle className="h-5 w-5 mr-2 text-yellow-600" />
                      Policy Citations
                    </h3>
                    <div className="space-y-2">
                      {response.context.policy_citations.map((citation, index) => (
                        <div key={index} className="p-3 bg-yellow-50 rounded-lg">
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
                <MessageSquare className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-500">Generate a communication draft to see results here</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
