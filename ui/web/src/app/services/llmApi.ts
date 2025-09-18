/**
 * API service for LLM message tracking
 */

const GATEWAY_URL = process.env.NEXT_PUBLIC_GATEWAY_URL || 'http://localhost:8080'

export interface LLMMessage {
  id: string
  timestamp: string
  service: string
  prompt: string
  response: string
  model?: string
  tokens_used?: number
  duration_ms?: number
  metadata?: Record<string, any>
}

export interface LLMMessagesResponse {
  messages: LLMMessage[]
  total: number
}

export class LLMApi {
  /**
   * Fetch LLM messages from the backend
   */
  static async getMessages(limit: number = 50, service?: string): Promise<LLMMessagesResponse> {
    const params = new URLSearchParams()
    params.append('limit', limit.toString())
    if (service) {
      params.append('service', service)
    }

    const response = await fetch(`${GATEWAY_URL}/llm/messages?${params}`)
    
    if (!response.ok) {
      throw new Error(`Failed to fetch LLM messages: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Track a new LLM message
   */
  static async trackMessage(message: LLMMessage): Promise<void> {
    const response = await fetch(`${GATEWAY_URL}/llm/track`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(message),
    })

    if (!response.ok) {
      throw new Error(`Failed to track LLM message: ${response.statusText}`)
    }
  }

  /**
   * Clear all LLM messages
   */
  static async clearMessages(): Promise<void> {
    const response = await fetch(`${GATEWAY_URL}/llm/messages`, {
      method: 'DELETE',
    })

    if (!response.ok) {
      throw new Error(`Failed to clear LLM messages: ${response.statusText}`)
    }
  }

  /**
   * Send a custom event to notify components of new messages
   */
  static notifyNewMessage(message: LLMMessage): void {
    const event = new CustomEvent('llm-message', { detail: message })
    window.dispatchEvent(event)
  }
}
