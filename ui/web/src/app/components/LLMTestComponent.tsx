'use client'

import { useState } from 'react'
import { Bot, TestTube } from 'lucide-react'

interface LLMTestComponentProps {
  className?: string
}

export default function LLMTestComponent({ className = '' }: LLMTestComponentProps) {
  const [testing, setTesting] = useState(false)
  const [testingMessages, setTestingMessages] = useState(false)

  const testLLMCall = async () => {
    setTesting(true)
    try {
      console.log('Testing LLM call...')
      
      // First, let's check if we can reach the gateway
      const gatewayUrl = process.env.NEXT_PUBLIC_GATEWAY_URL || 'http://localhost:8080'
      console.log('Gateway URL:', gatewayUrl)
      
      // Test the test_llm endpoint which uses the prompt manager
      const response = await fetch(`${gatewayUrl}/test_llm`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      })

      console.log('Response status:', response.status)
      console.log('Response headers:', Object.fromEntries(response.headers.entries()))

      if (response.ok) {
        const result = await response.json()
        console.log('LLM Test Result:', result)
        
        // Check if LLM message is in the response
        if (result.llm_message) {
          console.log('LLM Message tracked:', result.llm_message)
          // Dispatch custom event to notify the LLM display component
          const event = new CustomEvent('llm-message', { detail: result.llm_message })
          window.dispatchEvent(event)
        } else {
          console.log('No LLM message found in response')
        }
      } else {
        const errorText = await response.text()
        console.error('Response error:', errorText)
      }
    } catch (error) {
      console.error('LLM Test Error:', error)
    } finally {
      setTesting(false)
    }
  }

  const testMessagesEndpoint = async () => {
    setTestingMessages(true)
    try {
      console.log('Testing LLM messages endpoint...')
      const gatewayUrl = process.env.NEXT_PUBLIC_GATEWAY_URL || 'http://localhost:8080'
      const response = await fetch(`${gatewayUrl}/llm/messages?limit=10`)
      
      console.log('Messages endpoint status:', response.status)
      
      if (response.ok) {
        const result = await response.json()
        console.log('Messages endpoint result:', result)
      } else {
        const errorText = await response.text()
        console.error('Messages endpoint error:', errorText)
      }
    } catch (error) {
      console.error('Messages endpoint test error:', error)
    } finally {
      setTestingMessages(false)
    }
  }

  return (
    <div className={`bg-white/95 backdrop-blur-sm rounded-xl shadow-lg border-2 border-gray-200 p-4 ${className}`}>
      <div className="flex items-center space-x-3 mb-4">
        <div className="bg-blue-100 p-2 rounded-lg">
          <TestTube className="h-5 w-5 text-blue-600" />
        </div>
        <div>
          <h3 className="text-lg font-bold text-black">LLM Test</h3>
          <p className="text-sm text-gray-600">Test LLM message tracking</p>
        </div>
      </div>
      
      <div className="space-y-2">
        <button
          onClick={testLLMCall}
          disabled={testing}
          className="w-full bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center font-semibold transition-colors"
        >
          {testing ? (
            <>
              <Bot className="h-4 w-4 mr-2 animate-pulse" />
              Testing LLM...
            </>
          ) : (
            <>
              <Bot className="h-4 w-4 mr-2" />
              Test LLM Call
            </>
          )}
        </button>
        
        <button
          onClick={testMessagesEndpoint}
          disabled={testingMessages}
          className="w-full bg-green-600 text-white py-2 px-4 rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center font-semibold transition-colors"
        >
          {testingMessages ? (
            <>
              <TestTube className="h-4 w-4 mr-2 animate-pulse" />
              Testing Messages...
            </>
          ) : (
            <>
              <TestTube className="h-4 w-4 mr-2" />
              Test Messages Endpoint
            </>
          )}
        </button>
      </div>
    </div>
  )
}
