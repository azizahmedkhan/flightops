'use client'

import { useState, useEffect, useRef } from 'react'
import Link from 'next/link'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'react-hot-toast'
import { 
  MessageSquare, 
  Mail, 
  Smartphone, 
  Send, 
  Loader2,
  User,
  Phone,
  Plane,
  Calendar,
  Copy,
  CheckCircle,
  Clock,
  Bot,
  User as UserIcon
} from 'lucide-react'
import FlightNumberInput from '../components/FlightNumberInput'

const chatSessionSchema = z.object({
  customer_name: z.string().min(1, 'Name is required'),
  customer_email: z.string().email('Valid email is required'),
  customer_phone: z.string().optional(),
  flight_no: z.string().min(1, 'Flight number is required'),
  date: z.string().min(1, 'Date is required')
})

const messageSchema = z.object({
  message: z.string().min(1, 'Message is required')
})

const communicationSchema = z.object({
  customer_name: z.string().min(1, 'Name is required'),
  customer_email: z.string().email('Valid email is required'),
  customer_phone: z.string().optional(),
  flight_no: z.string().min(1, 'Flight number is required'),
  date: z.string().min(1, 'Date is required'),
  communication_type: z.enum(['email', 'sms', 'both']),
  tone: z.enum(['empathetic', 'professional', 'urgent'])
})

type ChatSessionForm = z.infer<typeof chatSessionSchema>
type MessageForm = z.infer<typeof messageSchema>
type CommunicationForm = z.infer<typeof communicationSchema>

interface ChatMessage {
  id: string
  type: 'customer' | 'agent'
  message: string
  timestamp: string
  customer_name?: string
  customer_email?: string
  customer_phone?: string
  flight_info?: any
  impact?: any
  options?: any[]
  citations?: string[]
}

interface Communication {
  communication_id: string
  type: string
  customer_name: string
  customer_email: string
  customer_phone?: string
  flight_no: string
  date: string
  content: string
  status: string
  sent_at: string
  tone: string
}

export default function CustomerChatPage() {
  const [activeTab, setActiveTab] = useState<'chat' | 'email' | 'sms'>('chat')
  const [chatSession, setChatSession] = useState<any>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [communications, setCommunications] = useState<Communication[]>([])
  const [loading, setLoading] = useState(false)
  const [copied, setCopied] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const chatSessionForm = useForm<ChatSessionForm>({
    resolver: zodResolver(chatSessionSchema),
    defaultValues: {
      customer_name: 'John Doe',
      customer_email: 'john.doe@example.com',
      customer_phone: '+1234567890',
      flight_no: '',
      date: ''
    }
  })

  const messageForm = useForm<MessageForm>({
    resolver: zodResolver(messageSchema),
    defaultValues: { message: '' }
  })

  const communicationForm = useForm<CommunicationForm>({
    resolver: zodResolver(communicationSchema),
    defaultValues: {
      customer_name: 'John Doe',
      customer_email: 'john.doe@example.com',
      customer_phone: '+1234567890',
      flight_no: '',
      date: '',
      communication_type: 'email',
      tone: 'empathetic'
    }
  })

  const handleChatFlightSelect = (suggestion: any) => {
    chatSessionForm.setValue('flight_no', suggestion.flight_no)
    chatSessionForm.setValue('date', suggestion.flight_date)
  }

  const handleCommunicationFlightSelect = (suggestion: any) => {
    communicationForm.setValue('flight_no', suggestion.flight_no)
    communicationForm.setValue('date', suggestion.flight_date)
  }

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const createChatSession = async (data: ChatSessionForm) => {
    setLoading(true)
    try {
      console.log('Creating chat session with data:', data)
      const res = await fetch(`${process.env.NEXT_PUBLIC_GATEWAY_URL || 'http://localhost:8080'}/customer-chat/session`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      })

      console.log('Response status:', res.status)
      if (!res.ok) {
        const errorText = await res.text()
        console.error('Error response:', errorText)
        throw new Error(`Failed to create chat session: ${res.status} ${errorText}`)
      }
      
      const result = await res.json()
      console.log('Chat session result:', result)
      setChatSession(result.session)
      setMessages([])
      toast.success('Chat session created!')
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred'
      toast.error(`Failed to create chat session: ${errorMessage}`)
      console.error('Chat session error:', error)
    } finally {
      setLoading(false)
    }
  }

  const sendMessage = async (data: MessageForm) => {
    if (!chatSession) return

    setLoading(true)
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_GATEWAY_URL || 'http://localhost:8080'}/customer-chat/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: chatSession.session_id,
          message: data.message,
          customer_name: chatSession.customer_name,
          customer_email: chatSession.customer_email,
          customer_phone: chatSession.customer_phone
        })
      })

      if (!res.ok) throw new Error('Failed to send message')
      
      const result = await res.json()
      setMessages(prev => [...prev, result.customer_message, result.ai_response])
      messageForm.reset()
      toast.success('Message sent!')
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred'
      toast.error(`Failed to send message: ${errorMessage}`)
      console.error('Send message error:', error)
    } finally {
      setLoading(false)
    }
  }

  const sendCommunication = async (data: CommunicationForm) => {
    setLoading(true)
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_GATEWAY_URL || 'http://localhost:8080'}/customer-chat/communication/send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      })

      if (!res.ok) throw new Error('Failed to send communication')
      
      const result = await res.json()
      setCommunications(prev => [result, ...prev])
      toast.success(`${data.communication_type.toUpperCase()} sent successfully!`)
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred'
      toast.error(`Failed to send communication: ${errorMessage}`)
      console.error('Send communication error:', error)
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

  const testConnection = async () => {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_GATEWAY_URL || 'http://localhost:8080'}/customer-chat/test`)
      const result = await res.json()
      console.log('Connection test result:', result)
      toast.success('Connection test successful!')
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred'
      console.error('Connection test error:', error)
      toast.error(`Connection test failed: ${errorMessage}`)
    }
  }

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString()
  }

  return (
    <div className="relative min-h-screen">
      {/* AiAir Airplane Background */}
      <div className="absolute inset-0 bg-gradient-to-br from-slate-50 via-gray-100 to-slate-200">
        <div className="absolute inset-0 opacity-15">
          {/* Airplane silhouette shapes */}
          <div className="absolute top-16 right-16 w-80 h-32 bg-gradient-to-r from-slate-400 to-slate-600 rounded-full transform rotate-12 opacity-20"></div>
          <div className="absolute top-32 right-8 w-64 h-24 bg-gradient-to-r from-slate-300 to-slate-500 rounded-full transform rotate-6 opacity-15"></div>
          <div className="absolute top-48 right-24 w-48 h-16 bg-gradient-to-r from-slate-400 to-slate-600 rounded-full transform -rotate-3 opacity-10"></div>
          
          {/* Cloud formations */}
          <div className="absolute top-24 left-12 w-72 h-40 bg-gradient-to-r from-gray-200 to-gray-300 rounded-full transform -rotate-12 opacity-20"></div>
          <div className="absolute top-64 left-32 w-56 h-32 bg-gradient-to-r from-gray-100 to-gray-200 rounded-full transform rotate-6 opacity-15"></div>
          
          {/* Additional airplane elements */}
          <div className="absolute bottom-32 right-1/3 w-96 h-24 bg-gradient-to-r from-slate-300 to-slate-500 rounded-full transform rotate-45 opacity-10"></div>
          <div className="absolute bottom-48 right-1/4 w-64 h-20 bg-gradient-to-r from-slate-400 to-slate-600 rounded-full transform -rotate-12 opacity-8"></div>
          
          {/* Subtle patterns */}
          <div className="absolute top-1/2 left-1/4 w-2 h-32 bg-slate-400 transform rotate-12 opacity-20"></div>
          <div className="absolute top-1/3 right-1/3 w-2 h-24 bg-slate-500 transform -rotate-6 opacity-15"></div>
          <div className="absolute bottom-1/3 left-1/2 w-2 h-20 bg-slate-400 transform rotate-45 opacity-10"></div>
        </div>
      </div>

      {/* Header */}
      <header className="bg-black text-white relative z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between py-6">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <div className="w-8 h-8 bg-white rounded-full flex items-center justify-center">
                  <MessageSquare className="h-5 w-5 text-black" />
                </div>
                <div>
                  <h1 className="text-2xl font-bold">Customer Communication</h1>
                  <p className="text-sm text-gray-300">Test customer communication channels</p>
                </div>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <Link href="/" className="text-sm font-medium text-white hover:text-gray-200">
                Back to Home
              </Link>
              <button
                onClick={testConnection}
                className="px-6 py-2 bg-white text-black rounded-lg hover:bg-gray-100 text-sm font-medium transition-colors"
              >
                Test Connection
              </button>
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
                { id: 'chat', label: 'Live Chat', icon: MessageSquare },
                { id: 'email', label: 'Email Test', icon: Mail },
                { id: 'sms', label: 'SMS Test', icon: Smartphone }
              ].map((tab) => {
                const Icon = tab.icon
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id as any)}
                    className={`flex items-center py-4 px-1 border-b-2 font-semibold text-sm transition-colors ${
                      activeTab === tab.id
                        ? 'border-black text-black'
                        : 'border-transparent text-gray-600 hover:text-black hover:border-gray-300'
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

        {/* Chat Tab */}
        {activeTab === 'chat' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Chat Session Setup */}
            <div className="bg-white/95 backdrop-blur-sm rounded-xl shadow-lg p-6 border-2 border-gray-200">
              <h2 className="text-xl font-bold text-black mb-6">Start Chat Session</h2>
              
              <form onSubmit={chatSessionForm.handleSubmit(createChatSession)} className="space-y-5">
                <div>
                  <label className="block text-sm font-semibold text-gray-900 mb-2">
                    Customer Name
                  </label>
                  <input
                    {...chatSessionForm.register('customer_name')}
                    className="w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-black focus:border-transparent transition-colors"
                    placeholder="John Doe"
                  />
                  {chatSessionForm.formState.errors.customer_name && (
                    <p className="mt-1 text-sm text-red-600 font-medium">
                      {chatSessionForm.formState.errors.customer_name.message}
                    </p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-semibold text-gray-900 mb-2">
                    Email
                  </label>
                  <input
                    {...chatSessionForm.register('customer_email')}
                    type="email"
                    className="w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-black focus:border-transparent transition-colors"
                    placeholder="john.doe@example.com"
                  />
                  {chatSessionForm.formState.errors.customer_email && (
                    <p className="mt-1 text-sm text-red-600 font-medium">
                      {chatSessionForm.formState.errors.customer_email.message}
                    </p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-semibold text-gray-900 mb-2">
                    Phone (Optional)
                  </label>
                  <input
                    {...chatSessionForm.register('customer_phone')}
                    className="w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-black focus:border-transparent transition-colors"
                    placeholder="+1234567890"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-semibold text-gray-900 mb-2">
                      Flight Number
                    </label>
                    <FlightNumberInput
                      value={chatSessionForm.watch('flight_no') || ''}
                      onChange={(value) => chatSessionForm.setValue('flight_no', value)}
                      onSelect={handleChatFlightSelect}
                      error={chatSessionForm.formState.errors.flight_no?.message}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-gray-900 mb-2">
                      Date
                    </label>
                    <input
                      {...chatSessionForm.register('date')}
                      type="date"
                      className="w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-black focus:border-transparent transition-colors"
                    />
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
                      Creating...
                    </>
                  ) : (
                    <>
                      <MessageSquare className="h-5 w-5 mr-2" />
                      Start Chat
                    </>
                  )}
                </button>
              </form>
            </div>

            {/* Chat Interface */}
            <div className="lg:col-span-2 bg-white/95 backdrop-blur-sm rounded-xl shadow-lg border-2 border-gray-200 flex flex-col h-96">
              {chatSession ? (
                <>
                  {/* Chat Header */}
                  <div className="p-6 border-b-2 border-gray-200 bg-gray-50 rounded-t-xl">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <div className="bg-black p-2 rounded-full">
                          <UserIcon className="h-5 w-5 text-white" />
                        </div>
                        <div>
                          <h3 className="font-bold text-black">{chatSession.customer_name}</h3>
                          <p className="text-sm text-gray-600 font-medium">{chatSession.customer_email}</p>
                        </div>
                      </div>
                      <div className="text-sm text-gray-600 font-semibold">
                        Flight {chatSession.flight_no} • {chatSession.date}
                      </div>
                    </div>
                  </div>

                  {/* Messages */}
                  <div className="flex-1 p-6 overflow-y-auto space-y-4">
                    {messages.map((message) => (
                      <div
                        key={message.id}
                        className={`flex ${message.type === 'customer' ? 'justify-end' : 'justify-start'}`}
                      >
                        <div
                          className={`max-w-xs lg:max-w-md px-4 py-3 rounded-lg ${
                            message.type === 'customer'
                              ? 'bg-black text-white'
                              : 'bg-gray-100 text-gray-900 border border-gray-200'
                          }`}
                        >
                          <div className="flex items-center space-x-2 mb-1">
                            {message.type === 'customer' ? (
                              <UserIcon className="h-4 w-4" />
                            ) : (
                              <Bot className="h-4 w-4" />
                            )}
                            <span className="text-xs opacity-75 font-medium">
                              {formatTime(message.timestamp)}
                            </span>
                          </div>
                          <p className="text-sm font-medium">{message.message}</p>
                          
                          {/* Flight Info for Agent Messages */}
                          {message.type === 'agent' && message.flight_info && (
                            <div className="mt-2 pt-2 border-t border-gray-300">
                              <p className="text-xs font-semibold">Flight Status: {message.flight_info.status}</p>
                              <p className="text-xs">Route: {message.flight_info.origin} → {message.flight_info.destination}</p>
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                    <div ref={messagesEndRef} />
                  </div>

                  {/* Message Input */}
                  <div className="p-6 border-t-2 border-gray-200">
                    <form onSubmit={messageForm.handleSubmit(sendMessage)} className="flex space-x-3">
                      <input
                        {...messageForm.register('message')}
                        className="flex-1 px-4 py-3 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-black focus:border-transparent transition-colors"
                        placeholder="Type your message..."
                        disabled={loading}
                      />
                      <button
                        type="submit"
                        disabled={loading}
                        className="bg-black text-white px-6 py-3 rounded-lg hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed font-semibold transition-colors"
                      >
                        <Send className="h-5 w-5" />
                      </button>
                    </form>
                  </div>
                </>
              ) : (
                <div className="flex-1 flex items-center justify-center text-gray-500">
                  <div className="text-center">
                    <MessageSquare className="h-16 w-16 mx-auto mb-4 text-gray-400" />
                    <p className="text-xl font-bold text-gray-600">Start a chat session to begin testing</p>
                    <p className="text-sm text-gray-500 mt-2">Fill out the form on the left to create a new chat session</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Email Tab */}
        {activeTab === 'email' && (
          <div className="bg-white/95 backdrop-blur-sm rounded-xl shadow-lg p-8 border-2 border-gray-200">
            <h2 className="text-2xl font-bold text-black mb-8">Email Communication Test</h2>
            
            <form onSubmit={communicationForm.handleSubmit(sendCommunication)} className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-semibold text-gray-900 mb-2">
                    Customer Name
                  </label>
                  <input
                    {...communicationForm.register('customer_name')}
                    className="w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-black focus:border-transparent transition-colors"
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-gray-900 mb-2">
                    Email Address
                  </label>
                  <input
                    {...communicationForm.register('customer_email')}
                    type="email"
                    className="w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-black focus:border-transparent transition-colors"
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-gray-900 mb-2">
                    Flight Number
                  </label>
                  <FlightNumberInput
                    value={communicationForm.watch('flight_no') || ''}
                    onChange={(value) => communicationForm.setValue('flight_no', value)}
                    onSelect={handleCommunicationFlightSelect}
                    error={communicationForm.formState.errors.flight_no?.message}
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-gray-900 mb-2">
                    Date
                  </label>
                  <input
                    {...communicationForm.register('date')}
                    type="date"
                    className="w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-black focus:border-transparent transition-colors"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-semibold text-gray-900 mb-2">
                    Communication Type
                  </label>
                  <select
                    {...communicationForm.register('communication_type')}
                    className="w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-black focus:border-transparent transition-colors"
                  >
                    <option value="email">Email</option>
                    <option value="both">Email + SMS</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-semibold text-gray-900 mb-2">
                    Tone
                  </label>
                  <select
                    {...communicationForm.register('tone')}
                    className="w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-black focus:border-transparent transition-colors"
                  >
                    <option value="empathetic">Empathetic</option>
                    <option value="professional">Professional</option>
                    <option value="urgent">Urgent</option>
                  </select>
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
                    Sending...
                  </>
                ) : (
                  <>
                    <Mail className="h-5 w-5 mr-2" />
                    Send Email
                  </>
                )}
              </button>
            </form>
          </div>
        )}

        {/* SMS Tab */}
        {activeTab === 'sms' && (
          <div className="bg-white/95 backdrop-blur-sm rounded-xl shadow-lg p-8 border-2 border-gray-200">
            <h2 className="text-2xl font-bold text-black mb-8">SMS Communication Test</h2>
            
            <form onSubmit={communicationForm.handleSubmit(sendCommunication)} className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-semibold text-gray-900 mb-2">
                    Customer Name
                  </label>
                  <input
                    {...communicationForm.register('customer_name')}
                    className="w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-black focus:border-transparent transition-colors"
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-gray-900 mb-2">
                    Phone Number
                  </label>
                  <input
                    {...communicationForm.register('customer_phone')}
                    className="w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-black focus:border-transparent transition-colors"
                    placeholder="+1234567890"
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-gray-900 mb-2">
                    Flight Number
                  </label>
                  <FlightNumberInput
                    value={communicationForm.watch('flight_no') || ''}
                    onChange={(value) => communicationForm.setValue('flight_no', value)}
                    onSelect={handleCommunicationFlightSelect}
                    error={communicationForm.formState.errors.flight_no?.message}
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-gray-900 mb-2">
                    Date
                  </label>
                  <input
                    {...communicationForm.register('date')}
                    type="date"
                    className="w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-black focus:border-transparent transition-colors"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-semibold text-gray-900 mb-2">
                    Communication Type
                  </label>
                  <select
                    {...communicationForm.register('communication_type')}
                    className="w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-black focus:border-transparent transition-colors"
                  >
                    <option value="sms">SMS</option>
                    <option value="both">SMS + Email</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-semibold text-gray-900 mb-2">
                    Tone
                  </label>
                  <select
                    {...communicationForm.register('tone')}
                    className="w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-black focus:border-transparent transition-colors"
                  >
                    <option value="empathetic">Empathetic</option>
                    <option value="professional">Professional</option>
                    <option value="urgent">Urgent</option>
                  </select>
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
                    Sending...
                  </>
                ) : (
                  <>
                    <Smartphone className="h-5 w-5 mr-2" />
                    Send SMS
                  </>
                )}
              </button>
            </form>
          </div>
        )}

        {/* Communication History */}
        {communications.length > 0 && (
          <div className="mt-8 bg-white/95 backdrop-blur-sm rounded-xl shadow-lg p-8 border-2 border-gray-200">
            <h2 className="text-2xl font-bold text-black mb-8">Recent Communications</h2>
            <div className="space-y-6">
              {communications.map((comm) => (
                <div key={comm.communication_id} className="p-6 border-2 border-gray-200 rounded-lg hover:border-gray-300 transition-colors">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center space-x-3">
                      {comm.type === 'email' ? (
                        <div className="bg-black p-2 rounded-full">
                          <Mail className="h-5 w-5 text-white" />
                        </div>
                      ) : (
                        <div className="bg-black p-2 rounded-full">
                          <Smartphone className="h-5 w-5 text-white" />
                        </div>
                      )}
                      <span className="font-bold text-black">{comm.customer_name}</span>
                      <span className="text-sm text-gray-500">•</span>
                      <span className="text-sm font-semibold text-gray-600">{comm.type.toUpperCase()}</span>
                    </div>
                    <div className="flex items-center space-x-3">
                      <span className="text-sm text-gray-600 font-medium">{comm.sent_at}</span>
                      <button
                        onClick={() => copyToClipboard(comm.content)}
                        className="text-sm text-black hover:text-gray-600 transition-colors font-semibold"
                      >
                        {copied ? <CheckCircle className="h-5 w-5" /> : <Copy className="h-5 w-5" />}
                      </button>
                    </div>
                  </div>
                  <p className="text-sm text-gray-800 mb-4 font-medium leading-relaxed">{comm.content}</p>
                  <div className="text-xs text-gray-600 font-semibold">
                    Flight {comm.flight_no} • {comm.date} • {comm.tone} tone
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
