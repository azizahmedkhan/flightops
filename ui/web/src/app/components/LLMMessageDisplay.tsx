'use client'

import { useState, useEffect } from 'react'
import { 
  MessageSquare, 
  ChevronDown, 
  ChevronUp, 
  Copy, 
  CheckCircle, 
  Clock,
  Bot,
  User,
  Trash2,
  RefreshCw
} from 'lucide-react'
import { toast } from 'react-hot-toast'
import { LLMApi, LLMMessage } from '../services/llmApi'

interface LLMMessageDisplayProps {
  className?: string
}

export default function LLMMessageDisplay({ className = '' }: LLMMessageDisplayProps) {
  const [messages, setMessages] = useState<LLMMessage[]>([])
  const [isExpanded, setIsExpanded] = useState(false)
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [llmApi] = useState(() => new LLMApi())

  // Load messages from API on mount
  useEffect(() => {
    loadMessages()
  }, [])

  // Listen for new messages from the global event system
  useEffect(() => {
    const handleNewMessage = (event: CustomEvent) => {
      const newMessage = event.detail
      setMessages(prev => {
        const updated = [newMessage, ...prev].slice(0, 50) // Keep last 50 messages
        return updated
      })
    }

    window.addEventListener('llm-message', handleNewMessage as EventListener)
    return () => {
      window.removeEventListener('llm-message', handleNewMessage as EventListener)
    }
  }, [])

  const loadMessages = async () => {
    setLoading(true)
    try {
      console.log('Loading LLM messages...')
      const response = await llmApi.getMessages(50)
      console.log('LLM messages response:', response)
      setMessages(response.messages)
    } catch (error) {
      console.error('Failed to load LLM messages:', error)
      toast.error('Failed to load LLM messages')
    } finally {
      setLoading(false)
    }
  }

  const copyToClipboard = async (text: string, messageId: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedId(messageId)
      toast.success('Copied to clipboard!')
      setTimeout(() => setCopiedId(null), 2000)
    } catch (error) {
      toast.error('Failed to copy to clipboard')
    }
  }

  const clearMessages = async () => {
    try {
      await llmApi.clearMessages()
      setMessages([])
      toast.success('Messages cleared')
    } catch (error) {
      console.error('Failed to clear messages:', error)
      toast.error('Failed to clear messages')
    }
  }

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString()
  }

  const formatDuration = (ms?: number) => {
    if (!ms) return 'N/A'
    return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`
  }

  const getServiceColor = (service: string) => {
    const colors: Record<string, string> = {
      'agent-svc': 'bg-blue-100 text-blue-800 border-blue-200',
      'comms-svc': 'bg-green-100 text-green-800 border-green-200',
      'crew-svc': 'bg-purple-100 text-purple-800 border-purple-200',
      'predictive-svc': 'bg-orange-100 text-orange-800 border-orange-200',
      'retrieval-svc': 'bg-gray-100 text-gray-800 border-gray-200',
      'customer-chat-svc': 'bg-pink-100 text-pink-800 border-pink-200',
      'gateway-api': 'bg-indigo-100 text-indigo-800 border-indigo-200'
    }
    return colors[service] || 'bg-gray-100 text-gray-800 border-gray-200'
  }

  if (messages.length === 0) {
    return (
      <div className={`bg-white/95 backdrop-blur-sm rounded-xl shadow-lg border-2 border-gray-200 ${className}`}>
        <div className="p-4 text-center">
          <MessageSquare className="h-8 w-8 text-gray-400 mx-auto mb-2" />
          <p className="text-sm text-gray-600 font-medium">No LLM messages yet</p>
          <p className="text-xs text-gray-500">Messages will appear here as you interact with the system</p>
        </div>
      </div>
    )
  }

  return (
    <div className={`bg-white/95 backdrop-blur-sm rounded-xl shadow-lg border-2 border-gray-200 ${className}`}>
      {/* Header */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="bg-black p-2 rounded-lg">
              <MessageSquare className="h-5 w-5 text-white" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-black">LLM Messages</h3>
              <p className="text-sm text-gray-600">{messages.length} message{messages.length !== 1 ? 's' : ''}</p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={loadMessages}
              disabled={loading}
              className="p-2 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors disabled:opacity-50"
              title="Refresh messages"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={clearMessages}
              className="p-2 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
              title="Clear messages"
            >
              <Trash2 className="h-4 w-4" />
            </button>
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
            >
              {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </button>
          </div>
        </div>
      </div>

      {/* Messages List */}
      {isExpanded && (
        <div className="max-h-96 overflow-y-auto">
          {messages.map((message) => (
            <div key={message.id} className="border-b border-gray-100 last:border-b-0">
              <div className="p-4">
                {/* Message Header */}
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center space-x-2">
                    <span className={`px-2 py-1 rounded-full text-xs font-semibold border ${getServiceColor(message.service)}`}>
                      {message.service}
                    </span>
                    <div className="flex items-center text-xs text-gray-500">
                      <Clock className="h-3 w-3 mr-1" />
                      {formatTimestamp(message.timestamp)}
                    </div>
                    {message.duration_ms && (
                      <div className="text-xs text-gray-500">
                        {formatDuration(message.duration_ms)}
                      </div>
                    )}
                    {message.tokens_used && (
                      <div className="text-xs text-gray-500">
                        {message.tokens_used} tokens
                      </div>
                    )}
                  </div>
                  <button
                    onClick={() => copyToClipboard(JSON.stringify(message, null, 2), message.id)}
                    className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
                    title="Copy message"
                  >
                    {copiedId === message.id ? (
                      <CheckCircle className="h-4 w-4 text-green-600" />
                    ) : (
                      <Copy className="h-4 w-4" />
                    )}
                  </button>
                </div>

                {/* Prompt */}
                <div className="mb-3">
                  <div className="flex items-center mb-2">
                    <User className="h-4 w-4 text-blue-600 mr-2" />
                    <span className="text-sm font-semibold text-gray-700">Prompt</span>
                  </div>
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                    <pre className="text-xs text-gray-800 whitespace-pre-wrap font-mono">
                      {message.prompt}
                    </pre>
                  </div>
                </div>

                {/* Response */}
                <div>
                  <div className="flex items-center mb-2">
                    <Bot className="h-4 w-4 text-green-600 mr-2" />
                    <span className="text-sm font-semibold text-gray-700">Response</span>
                    {message.model && (
                      <span className="ml-2 text-xs text-gray-500">({message.model})</span>
                    )}
                  </div>
                  <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                    <pre className="text-xs text-gray-800 whitespace-pre-wrap font-mono">
                      {message.response}
                    </pre>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
