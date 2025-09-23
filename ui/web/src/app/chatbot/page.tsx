"use client";

import React, { useState, useEffect, useRef } from 'react';

interface Message {
  id: string;
  type: 'user' | 'bot' | 'system';
  content: string;
  timestamp: string;
  metadata?: any;
  isComplete?: boolean;
}

interface Session {
  session_id: string;
  customer_name: string;
  customer_email: string;
  flight_no?: string;
  date?: string;
}

const ChatbotPage: React.FC = () => {
  const [session, setSession] = useState<Session | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [connectionStats, setConnectionStats] = useState<any>(null);
  const [isReconnecting, setIsReconnecting] = useState(false);
  const [lastActivity, setLastActivity] = useState<Date | null>(null);
  
  const wsRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const heartbeatIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const clientIdRef = useRef<string | null>(null);
  const sessionIdRef = useRef<string | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Save messages to localStorage whenever they change
  useEffect(() => {
    if (sessionIdRef.current && messages.length > 0) {
      const chatHistory = {
        sessionId: sessionIdRef.current,
        messages: messages,
        lastSaved: new Date().toISOString()
      };
      localStorage.setItem(`chatbot-history-${sessionIdRef.current}`, JSON.stringify(chatHistory));
    }
  }, [messages]);

  // Load chat history for a specific session
  const loadChatHistory = (sessionId: string) => {
    try {
      const savedHistory = localStorage.getItem(`chatbot-history-${sessionId}`);
      if (savedHistory) {
        const history = JSON.parse(savedHistory);
        if (history.messages && Array.isArray(history.messages)) {
          setMessages(history.messages);
          console.log(`Loaded ${history.messages.length} messages from chat history`);
        }
      }
    } catch (error) {
      console.error('Error loading chat history:', error);
    }
  };

  // Clear chat history
  const clearChatHistory = () => {
    if (sessionIdRef.current) {
      localStorage.removeItem(`chatbot-history-${sessionIdRef.current}`);
      setMessages([]);
      console.log('Chat history cleared');
    }
  };

  useEffect(() => {
    return () => {
      // Cleanup on unmount
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (heartbeatIntervalRef.current) {
        clearInterval(heartbeatIntervalRef.current);
      }
    };
  }, []);

  // Cleanup function
  const cleanup = () => {
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
      heartbeatIntervalRef.current = null;
    }
  };

  // Heartbeat function to keep connection alive
  const startHeartbeat = () => {
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
    }
    
    heartbeatIntervalRef.current = setInterval(() => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        try {
          wsRef.current.send(JSON.stringify({ type: 'ping' }));
          setLastActivity(new Date());
        } catch (error) {
          console.error('Heartbeat failed:', error);
          handleDisconnection();
        }
      } else {
        handleDisconnection();
      }
    }, 30000); // Send ping every 30 seconds
  };

  // Handle disconnection - manual reconnection only
  const handleDisconnection = () => {
    setIsConnected(false);
    cleanup();
    
    addMessage({
      id: Date.now().toString(),
      type: 'system',
      content: 'Connection lost. Click the "Reconnect" button to restore connection.',
      timestamp: new Date().toISOString()
    });
  };

  // Manual reconnection function
  const reconnectWebSocket = async () => {
    if (!sessionIdRef.current) {
      setError('No active session to reconnect');
      return;
    }

    try {
      setIsReconnecting(true);
      setError(null);
      
      // Close existing connection if any
      if (wsRef.current) {
        wsRef.current.close();
      }
      
      // Generate new client ID for reconnection
      const newClientId = `client-${Date.now()}`;
      clientIdRef.current = newClientId;
      
      const wsUrl = `ws://localhost:8088/ws/${sessionIdRef.current}/${newClientId}`;
      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        setIsConnected(true);
        setIsReconnecting(false);
        setLastActivity(new Date());
        startHeartbeat();
        
        // Load chat history if not already loaded
        if (sessionIdRef.current) {
          loadChatHistory(sessionIdRef.current);
        }
        
        addMessage({
          id: Date.now().toString(),
          type: 'system',
          content: 'Successfully reconnected to chatbot!',
          timestamp: new Date().toISOString()
        });
      };

      wsRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          // Handle ping responses
          if (data.type === 'pong') {
            setLastActivity(new Date());
            return;
          }
          
          if (data.type === 'chunk') {
            // Handle streaming response chunks
            setMessages(prev => {
              const lastMessage = prev[prev.length - 1];
              if (lastMessage && lastMessage.type === 'bot' && !lastMessage.isComplete) {
                // Update last message with new chunk
                const updatedMessages = [...prev];
                updatedMessages[updatedMessages.length - 1] = {
                  ...lastMessage,
                  content: lastMessage.content + data.content
                };
                return updatedMessages;
              } else {
                // Start new message
                return [...prev, {
                  id: Date.now().toString(),
                  type: 'bot',
                  content: data.content,
                  timestamp: data.timestamp,
                  isComplete: false
                }];
              }
            });
          } else if (data.type === 'complete') {
            // Mark message as complete
            setMessages(prev => {
              const updatedMessages = [...prev];
              const lastMessage = updatedMessages[updatedMessages.length - 1];
              if (lastMessage && lastMessage.type === 'bot') {
                updatedMessages[updatedMessages.length - 1] = {
                  ...lastMessage,
                  content: data.content,
                  isComplete: true,
                  metadata: data.metadata
                };
              }
              return updatedMessages;
            });
          } else if (data.type === 'error') {
            addMessage({
              id: Date.now().toString(),
              type: 'system',
              content: `Error: ${data.content}`,
              timestamp: data.timestamp
            });
          }
        } catch (err) {
          console.error('Error parsing WebSocket message:', err);
        }
      };

      wsRef.current.onclose = () => {
        setIsConnected(false);
        setIsReconnecting(false);
        handleDisconnection();
      };

      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        setError('WebSocket connection error');
        setIsReconnecting(false);
      };

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reconnect WebSocket');
      setIsReconnecting(false);
    }
  };

  const createSession = async () => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await fetch('http://localhost:8088/chat/session', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          customer_name: 'Test User',
          customer_email: 'test@example.com',
          flight_no: 'NZ123',
          date: '2025-01-17'
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const sessionData = await response.json();
      setSession(sessionData.context);
      
      // Store session ID for reconnection
      sessionIdRef.current = sessionData.session_id;
      
      // Load existing chat history for this session
      loadChatHistory(sessionData.session_id);
      
      // Connect WebSocket
      await connectWebSocket(sessionData.session_id);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create session');
    } finally {
      setIsLoading(false);
    }
  };

  const connectWebSocket = async (sessionId: string) => {
    try {
      const clientId = `client-${Date.now()}`;
      clientIdRef.current = clientId;
      const wsUrl = `ws://localhost:8088/ws/${sessionId}/${clientId}`;
      
      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        setIsConnected(true);
        setLastActivity(new Date());
        startHeartbeat();
        
        addMessage({
          id: Date.now().toString(),
          type: 'system',
          content: 'Connected to chatbot. You can start chatting!',
          timestamp: new Date().toISOString()
        });
      };

      wsRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          // Handle ping responses
          if (data.type === 'pong') {
            setLastActivity(new Date());
            return;
          }
          
          if (data.type === 'chunk') {
            // Handle streaming response chunks
            setMessages(prev => {
              const lastMessage = prev[prev.length - 1];
              if (lastMessage && lastMessage.type === 'bot' && !lastMessage.isComplete) {
                // Update last message with new chunk
                const updatedMessages = [...prev];
                updatedMessages[updatedMessages.length - 1] = {
                  ...lastMessage,
                  content: lastMessage.content + data.content
                };
                return updatedMessages;
              } else {
                // Start new message
                return [...prev, {
                  id: Date.now().toString(),
                  type: 'bot',
                  content: data.content,
                  timestamp: data.timestamp,
                  isComplete: false
                }];
              }
            });
          } else if (data.type === 'complete') {
            // Mark message as complete
            setMessages(prev => {
              const updatedMessages = [...prev];
              const lastMessage = updatedMessages[updatedMessages.length - 1];
              if (lastMessage && lastMessage.type === 'bot') {
                updatedMessages[updatedMessages.length - 1] = {
                  ...lastMessage,
                  content: data.content,
                  isComplete: true,
                  metadata: data.metadata
                };
              }
              return updatedMessages;
            });
          } else if (data.type === 'error') {
            addMessage({
              id: Date.now().toString(),
              type: 'system',
              content: `Error: ${data.content}`,
              timestamp: data.timestamp
            });
          }
        } catch (err) {
          console.error('Error parsing WebSocket message:', err);
        }
      };

      wsRef.current.onclose = () => {
        setIsConnected(false);
        handleDisconnection();
      };

      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        setError('WebSocket connection error');
        handleDisconnection();
      };

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to connect WebSocket');
    }
  };

  const addMessage = (message: Message) => {
    setMessages(prev => [...prev, message]);
  };

  const sendMessage = async () => {
    if (!inputMessage.trim() || !wsRef.current || !isConnected) {
      return;
    }

    const messageText = inputMessage.trim();
    setInputMessage('');
    setLastActivity(new Date());

    // Add user message to UI
    addMessage({
      id: Date.now().toString(),
      type: 'user',
      content: messageText,
      timestamp: new Date().toISOString()
    });

    try {
      wsRef.current.send(JSON.stringify({ message: messageText }));
    } catch (err) {
      setError('Failed to send message');
      console.error('Error sending message:', err);
      handleDisconnection();
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const getConnectionStats = async () => {
    try {
      const response = await fetch('http://localhost:8088/stats');
      if (response.ok) {
        const stats = await response.json();
        setConnectionStats(stats);
      }
    } catch (err) {
      console.error('Failed to get connection stats:', err);
    }
  };

  const getHealthStatus = async () => {
    try {
      const response = await fetch('http://localhost:8088/health');
      if (response.ok) {
        const health = await response.json();
        console.log('Health status:', health);
      }
    } catch (err) {
      console.error('Failed to get health status:', err);
    }
  };

  useEffect(() => {
    // Get initial stats
    getConnectionStats();
    getHealthStatus();

    // Update stats every 10 seconds
    const interval = setInterval(getConnectionStats, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-gray-100">
      <div className="max-w-4xl mx-auto p-4">
        <div className="bg-white rounded-lg shadow-lg">
          {/* Header */}
          <div className="bg-blue-600 text-white p-4 rounded-t-lg">
            <div className="flex justify-between items-center">
              <div>
                <h1 className="text-2xl font-bold">Scalable Chatbot</h1>
                <p className="text-blue-100">Real-time chat with AI assistant</p>
              </div>
              <div className="text-right">
                <div className={`inline-block px-3 py-1 rounded-full text-sm ${
                  isConnected ? 'bg-green-500' : isReconnecting ? 'bg-yellow-500' : 'bg-red-500'
                }`}>
                  {isConnected ? 'Connected' : isReconnecting ? 'Reconnecting...' : 'Disconnected'}
                </div>
                {connectionStats && (
                  <div className="text-xs mt-1 text-blue-100">
                    {connectionStats.active_connections} active connections
                  </div>
                )}
                {lastActivity && (
                  <div className="text-xs mt-1 text-blue-100">
                    Last activity: {lastActivity.toLocaleTimeString()}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Chat Area */}
          <div className="h-96 overflow-y-auto p-4 space-y-4">
            {messages.length === 0 ? (
              <div className="text-center text-gray-500 mt-20">
                {!session ? (
                  <div>
                    <p className="text-lg mb-4">Welcome to the Scalable Chatbot!</p>
                    <p className="mb-4">This chatbot can handle 1000+ concurrent sessions.</p>
                    <button
                      onClick={createSession}
                      disabled={isLoading}
                      className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50"
                    >
                      {isLoading ? 'Creating Session...' : 'Start Chat'}
                    </button>
                  </div>
                ) : (
                  <p>Start typing to begin the conversation...</p>
                )}
              </div>
            ) : (
              messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                      message.type === 'user'
                        ? 'bg-blue-600 text-white'
                        : message.type === 'system'
                        ? 'bg-yellow-100 text-yellow-800 text-sm'
                        : 'bg-gray-200 text-gray-800'
                    }`}
                  >
                    <div className="whitespace-pre-wrap">{message.content}</div>
                    {message.metadata && (
                      <div className="text-xs mt-1 opacity-75">
                        {message.metadata.tokens_used && `Tokens: ${message.metadata.tokens_used}`}
                        {message.metadata.response_time_ms && ` | Time: ${message.metadata.response_time_ms}ms`}
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Error Display */}
          {error && (
            <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 mx-4 rounded">
              {error}
            </div>
          )}

          {/* Input Area */}
          {session && (
            <div className="p-4 border-t">
              <div className="flex space-x-2">
                <input
                  type="text"
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder={isConnected ? "Type your message..." : "Disconnected - click reconnect"}
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  disabled={!isConnected && !isReconnecting}
                />
                <div className="flex space-x-2">
                  {!isConnected && !isReconnecting ? (
                    <button
                      onClick={reconnectWebSocket}
                      className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700"
                    >
                      Reconnect
                    </button>
                  ) : (
                    <button
                      onClick={sendMessage}
                      disabled={!inputMessage.trim() || !isConnected || isReconnecting}
                      className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {isReconnecting ? 'Reconnecting...' : 'Send'}
                    </button>
                  )}
                  {session && messages.length > 0 && (
                    <button
                      onClick={clearChatHistory}
                      className="bg-gray-500 text-white px-4 py-2 rounded-lg hover:bg-gray-600"
                      title="Clear chat history"
                    >
                      Clear
                    </button>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Session Info */}
          {session && (
            <div className="bg-gray-50 p-4 border-t text-sm text-gray-600">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <strong>Session ID:</strong> {session.session_id}
                </div>
                <div>
                  <strong>Customer:</strong> {session.customer_name}
                </div>
                {session.flight_no && (
                  <div>
                    <strong>Flight:</strong> {session.flight_no}
                  </div>
                )}
                {session.date && (
                  <div>
                    <strong>Date:</strong> {session.date}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Performance Info */}
        <div className="mt-4 bg-white rounded-lg shadow p-4">
          <h3 className="text-lg font-semibold mb-2">Performance Metrics</h3>
          {connectionStats ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <div className="font-medium">Active Connections</div>
                <div className="text-2xl font-bold text-blue-600">
                  {connectionStats.active_connections}
                </div>
              </div>
              <div>
                <div className="font-medium">Active Sessions</div>
                <div className="text-2xl font-bold text-green-600">
                  {connectionStats.active_sessions}
                </div>
              </div>
              <div>
                <div className="font-medium">Messages in Chat</div>
                <div className="text-2xl font-bold text-purple-600">
                  {messages.length}
                </div>
              </div>
              <div>
                <div className="font-medium">Connection Status</div>
                <div className={`text-2xl font-bold ${
                  isConnected ? 'text-green-600' : isReconnecting ? 'text-yellow-600' : 'text-red-600'
                }`}>
                  {isConnected ? 'Live' : isReconnecting ? 'Reconnecting' : 'Offline'}
                </div>
              </div>
            </div>
          ) : (
            <p className="text-gray-500">Loading metrics...</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default ChatbotPage;
