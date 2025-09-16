'use client'

import { useState, useEffect, useRef } from 'react'
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
      flight_no: 'NZ123',
      date: '2025-09-17'
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
      flight_no: 'NZ123',
      date: '2025-09-17',
      communication_type: 'email',
      tone: 'empathetic'
    }
  })

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
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between py-6">
            <div className="flex items-center space-x-3">
              <MessageSquare className="h-8 w-8 text-blue-600" />
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Customer Communication</h1>
                <p className="text-sm text-gray-600">Test customer communication channels</p>
              </div>
            </div>
            <button
              onClick={testConnection}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
            >
              Test Connection
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Tab Navigation */}
        <div className="mb-8">
          <div className="border-b border-gray-200">
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
                    className={`flex items-center py-2 px-1 border-b-2 font-medium text-sm ${
                      activeTab === tab.id
                        ? 'border-blue-500 text-blue-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
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
            <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900 mb-6">Start Chat Session</h2>
              
              <form onSubmit={chatSessionForm.handleSubmit(createChatSession)} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Customer Name
                  </label>
                  <input
                    {...chatSessionForm.register('customer_name')}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="John Doe"
                  />
                  {chatSessionForm.formState.errors.customer_name && (
                    <p className="mt-1 text-sm text-red-600">
                      {chatSessionForm.formState.errors.customer_name.message}
                    </p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Email
                  </label>
                  <input
                    {...chatSessionForm.register('customer_email')}
                    type="email"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="john.doe@example.com"
                  />
                  {chatSessionForm.formState.errors.customer_email && (
                    <p className="mt-1 text-sm text-red-600">
                      {chatSessionForm.formState.errors.customer_email.message}
                    </p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Phone (Optional)
                  </label>
                  <input
                    {...chatSessionForm.register('customer_phone')}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="+1234567890"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Flight Number
                    </label>
                    <input
                      {...chatSessionForm.register('flight_no')}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="NZ123"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Date
                    </label>
                    <input
                      {...chatSessionForm.register('date')}
                      type="date"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
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
                      Creating...
                    </>
                  ) : (
                    <>
                      <MessageSquare className="h-4 w-4 mr-2" />
                      Start Chat
                    </>
                  )}
                </button>
              </form>
            </div>

            {/* Chat Interface */}
            <div className="lg:col-span-2 bg-white rounded-xl shadow-sm border border-gray-200 flex flex-col h-96">
              {chatSession ? (
                <>
                  {/* Chat Header */}
                  <div className="p-4 border-b border-gray-200 bg-gray-50 rounded-t-xl">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <div className="bg-blue-100 p-2 rounded-full">
                          <UserIcon className="h-5 w-5 text-blue-600" />
                        </div>
                        <div>
                          <h3 className="font-medium text-gray-900">{chatSession.customer_name}</h3>
                          <p className="text-sm text-gray-600">{chatSession.customer_email}</p>
                        </div>
                      </div>
                      <div className="text-sm text-gray-500">
                        Flight {chatSession.flight_no} • {chatSession.date}
                      </div>
                    </div>
                  </div>

                  {/* Messages */}
                  <div className="flex-1 p-4 overflow-y-auto space-y-4">
                    {messages.map((message) => (
                      <div
                        key={message.id}
                        className={`flex ${message.type === 'customer' ? 'justify-end' : 'justify-start'}`}
                      >
                        <div
                          className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                            message.type === 'customer'
                              ? 'bg-blue-600 text-white'
                              : 'bg-gray-100 text-gray-900'
                          }`}
                        >
                          <div className="flex items-center space-x-2 mb-1">
                            {message.type === 'customer' ? (
                              <UserIcon className="h-4 w-4" />
                            ) : (
                              <Bot className="h-4 w-4" />
                            )}
                            <span className="text-xs opacity-75">
                              {formatTime(message.timestamp)}
                            </span>
                          </div>
                          <p className="text-sm">{message.message}</p>
                          
                          {/* Flight Info for Agent Messages */}
                          {message.type === 'agent' && message.flight_info && (
                            <div className="mt-2 pt-2 border-t border-gray-300">
                              <p className="text-xs font-medium">Flight Status: {message.flight_info.status}</p>
                              <p className="text-xs">Route: {message.flight_info.origin} → {message.flight_info.destination}</p>
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                    <div ref={messagesEndRef} />
                  </div>

                  {/* Message Input */}
                  <div className="p-4 border-t border-gray-200">
                    <form onSubmit={messageForm.handleSubmit(sendMessage)} className="flex space-x-2">
                      <input
                        {...messageForm.register('message')}
                        className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        placeholder="Type your message..."
                        disabled={loading}
                      />
                      <button
                        type="submit"
                        disabled={loading}
                        className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <Send className="h-4 w-4" />
                      </button>
                    </form>
                  </div>
                </>
              ) : (
                <div className="flex-1 flex items-center justify-center text-gray-500">
                  <div className="text-center">
                    <MessageSquare className="h-12 w-12 mx-auto mb-4 text-gray-400" />
                    <p>Start a chat session to begin testing</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Email Tab */}
        {activeTab === 'email' && (
          <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900 mb-6">Email Communication Test</h2>
            
            <form onSubmit={communicationForm.handleSubmit(sendCommunication)} className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Customer Name
                  </label>
                  <input
                    {...communicationForm.register('customer_name')}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Email Address
                  </label>
                  <input
                    {...communicationForm.register('customer_email')}
                    type="email"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Flight Number
                  </label>
                  <input
                    {...communicationForm.register('flight_no')}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Date
                  </label>
                  <input
                    {...communicationForm.register('date')}
                    type="date"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Communication Type
                  </label>
                  <select
                    {...communicationForm.register('communication_type')}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="email">Email</option>
                    <option value="both">Email + SMS</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Tone
                  </label>
                  <select
                    {...communicationForm.register('tone')}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
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
                className="w-full bg-green-600 text-white py-2 px-4 rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Sending...
                  </>
                ) : (
                  <>
                    <Mail className="h-4 w-4 mr-2" />
                    Send Email
                  </>
                )}
              </button>
            </form>
          </div>
        )}

        {/* SMS Tab */}
        {activeTab === 'sms' && (
          <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900 mb-6">SMS Communication Test</h2>
            
            <form onSubmit={communicationForm.handleSubmit(sendCommunication)} className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Customer Name
                  </label>
                  <input
                    {...communicationForm.register('customer_name')}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Phone Number
                  </label>
                  <input
                    {...communicationForm.register('customer_phone')}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="+1234567890"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Flight Number
                  </label>
                  <input
                    {...communicationForm.register('flight_no')}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Date
                  </label>
                  <input
                    {...communicationForm.register('date')}
                    type="date"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Communication Type
                  </label>
                  <select
                    {...communicationForm.register('communication_type')}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="sms">SMS</option>
                    <option value="both">SMS + Email</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Tone
                  </label>
                  <select
                    {...communicationForm.register('tone')}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
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
                className="w-full bg-purple-600 text-white py-2 px-4 rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Sending...
                  </>
                ) : (
                  <>
                    <Smartphone className="h-4 w-4 mr-2" />
                    Send SMS
                  </>
                )}
              </button>
            </form>
          </div>
        )}

        {/* Communication History */}
        {communications.length > 0 && (
          <div className="mt-8 bg-white rounded-xl shadow-sm p-6 border border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900 mb-6">Recent Communications</h2>
            <div className="space-y-4">
              {communications.map((comm) => (
                <div key={comm.communication_id} className="p-4 border border-gray-200 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center space-x-2">
                      {comm.type === 'email' ? (
                        <Mail className="h-5 w-5 text-green-600" />
                      ) : (
                        <Smartphone className="h-5 w-5 text-purple-600" />
                      )}
                      <span className="font-medium">{comm.customer_name}</span>
                      <span className="text-sm text-gray-500">•</span>
                      <span className="text-sm text-gray-500">{comm.type.toUpperCase()}</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className="text-sm text-gray-500">{comm.sent_at}</span>
                      <button
                        onClick={() => copyToClipboard(comm.content)}
                        className="text-sm text-blue-600 hover:text-blue-800"
                      >
                        {copied ? <CheckCircle className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                      </button>
                    </div>
                  </div>
                  <p className="text-sm text-gray-700 mb-2">{comm.content}</p>
                  <div className="text-xs text-gray-500">
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
