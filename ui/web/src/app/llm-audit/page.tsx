'use client';

import React, { useState, useEffect } from 'react';
import { LLMApi, LLMMessage } from '../services/llmApi';

interface LLMAuditPageProps {}

export default function LLMAuditPage({}: LLMAuditPageProps) {
  const [messages, setMessages] = useState<LLMMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedService, setSelectedService] = useState<string>('');
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedMessages, setExpandedMessages] = useState<Set<string>>(new Set());
  const [sortBy, setSortBy] = useState<'timestamp' | 'service' | 'duration'>('timestamp');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  const llmApi = new LLMApi();

  // Get unique services from messages
  const services = Array.from(new Set(messages.map(msg => msg.service)));

  // Filter and sort messages
  const filteredMessages = messages
    .filter(msg => {
      const matchesService = !selectedService || msg.service === selectedService;
      const matchesSearch = !searchTerm || 
        msg.prompt.toLowerCase().includes(searchTerm.toLowerCase()) ||
        msg.response.toLowerCase().includes(searchTerm.toLowerCase()) ||
        msg.service.toLowerCase().includes(searchTerm.toLowerCase());
      return matchesService && matchesSearch;
    })
    .sort((a, b) => {
      let comparison = 0;
      switch (sortBy) {
        case 'timestamp':
          comparison = new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime();
          break;
        case 'service':
          comparison = a.service.localeCompare(b.service);
          break;
        case 'duration':
          comparison = (a.duration_ms || 0) - (b.duration_ms || 0);
          break;
      }
      return sortOrder === 'asc' ? comparison : -comparison;
    });

  const loadMessages = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await llmApi.getMessages(1000); // Get more messages for audit trail
      setMessages(response.messages);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load messages');
    } finally {
      setLoading(false);
    }
  };

  const clearMessages = async () => {
    try {
      await llmApi.clearMessages();
      setMessages([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to clear messages');
    }
  };

  const toggleMessageExpansion = (messageId: string) => {
    const newExpanded = new Set(expandedMessages);
    if (newExpanded.has(messageId)) {
      newExpanded.delete(messageId);
    } else {
      newExpanded.add(messageId);
    }
    setExpandedMessages(newExpanded);
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  const formatDuration = (durationMs?: number) => {
    if (!durationMs) return 'N/A';
    if (durationMs < 1000) return `${durationMs.toFixed(0)}ms`;
    return `${(durationMs / 1000).toFixed(2)}s`;
  };

  const getServiceColor = (service: string) => {
    const colors = {
      'agent-svc': 'bg-blue-100 text-blue-800 border-blue-200',
      'comms-svc': 'bg-green-100 text-green-800 border-green-200',
      'customer-chat-svc': 'bg-purple-100 text-purple-800 border-purple-200',
      'predictive-svc': 'bg-orange-100 text-orange-800 border-orange-200',
      'crew-svc': 'bg-pink-100 text-pink-800 border-pink-200',
      'knowledge-engine': 'bg-indigo-100 text-indigo-800 border-indigo-200',
      'ingest-svc': 'bg-gray-100 text-gray-800 border-gray-200',
      'gateway-api': 'bg-yellow-100 text-yellow-800 border-yellow-200',
    };
    return colors[service as keyof typeof colors] || 'bg-gray-100 text-gray-800 border-gray-200';
  };

  useEffect(() => {
    loadMessages();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-gray-100 p-6">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-gray-100 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">LLM Audit Trail</h1>
          <p className="text-gray-600">
            Complete audit trail of all LLM interactions across the FlightOps system
          </p>
        </div>

        {/* Controls */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
            {/* Service Filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Filter by Service
              </label>
              <select
                value={selectedService}
                onChange={(e) => setSelectedService(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">All Services</option>
                {services.map(service => (
                  <option key={service} value={service}>
                    {service}
                  </option>
                ))}
              </select>
            </div>

            {/* Search */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Search Messages
              </label>
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search prompts, responses..."
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Sort By */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Sort By
              </label>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as 'timestamp' | 'service' | 'duration')}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="timestamp">Timestamp</option>
                <option value="service">Service</option>
                <option value="duration">Duration</option>
              </select>
            </div>

            {/* Sort Order */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Order
              </label>
              <select
                value={sortOrder}
                onChange={(e) => setSortOrder(e.target.value as 'asc' | 'desc')}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="desc">Newest First</option>
                <option value="asc">Oldest First</option>
              </select>
            </div>
          </div>

          <div className="flex justify-between items-center">
            <div className="text-sm text-gray-600">
              Showing {filteredMessages.length} of {messages.length} messages
            </div>
            <div className="flex gap-2">
              <button
                onClick={loadMessages}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                Refresh
              </button>
              <button
                onClick={clearMessages}
                className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500"
              >
                Clear All
              </button>
            </div>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-md p-4 mb-6">
            <div className="flex">
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">Error</h3>
                <div className="mt-2 text-sm text-red-700">{error}</div>
              </div>
            </div>
          </div>
        )}

        {/* Messages List */}
        <div className="space-y-4">
          {filteredMessages.length === 0 ? (
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8 text-center">
              <div className="text-gray-500">
                {messages.length === 0 ? 'No LLM messages found' : 'No messages match your filters'}
              </div>
            </div>
          ) : (
            filteredMessages.map((message) => (
              <div
                key={message.id}
                className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden"
              >
                {/* Message Header */}
                <div className="px-6 py-4 border-b border-gray-200">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                      <span
                        className={`px-3 py-1 rounded-full text-xs font-medium border ${getServiceColor(
                          message.service
                        )}`}
                      >
                        {message.service}
                      </span>
                      <span className="text-sm text-gray-500">
                        {formatTimestamp(message.timestamp)}
                      </span>
                      {message.duration_ms && (
                        <span className="text-sm text-gray-500">
                          {formatDuration(message.duration_ms)}
                        </span>
                      )}
                      {message.tokens_used && (
                        <span className="text-sm text-gray-500">
                          {message.tokens_used} tokens
                        </span>
                      )}
                    </div>
                    <button
                      onClick={() => toggleMessageExpansion(message.id)}
                      className="text-gray-400 hover:text-gray-600 focus:outline-none"
                    >
                      {expandedMessages.has(message.id) ? (
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                        </svg>
                      ) : (
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                        </svg>
                      )}
                    </button>
                  </div>
                </div>

                {/* Message Content */}
                {expandedMessages.has(message.id) && (
                  <div className="px-6 py-4 space-y-4">
                    {/* Prompt */}
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="text-sm font-medium text-gray-900">Prompt</h4>
                        <button
                          onClick={() => copyToClipboard(message.prompt)}
                          className="text-xs text-blue-600 hover:text-blue-800 focus:outline-none"
                        >
                          Copy
                        </button>
                      </div>
                      <div className="bg-gray-50 rounded-md p-3 text-sm text-gray-800 whitespace-pre-wrap">
                        {message.prompt}
                      </div>
                    </div>

                    {/* Response */}
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="text-sm font-medium text-gray-900">Response</h4>
                        <button
                          onClick={() => copyToClipboard(message.response)}
                          className="text-xs text-blue-600 hover:text-blue-800 focus:outline-none"
                        >
                          Copy
                        </button>
                      </div>
                      <div className="bg-gray-50 rounded-md p-3 text-sm text-gray-800 whitespace-pre-wrap">
                        {message.response}
                      </div>
                    </div>

                    {/* Metadata */}
                    {message.metadata && Object.keys(message.metadata).length > 0 && (
                      <div>
                        <h4 className="text-sm font-medium text-gray-900 mb-2">Metadata</h4>
                        <div className="bg-gray-50 rounded-md p-3">
                          <pre className="text-xs text-gray-800 overflow-x-auto">
                            {JSON.stringify(message.metadata, null, 2)}
                          </pre>
                        </div>
                      </div>
                    )}

                    {/* Model Info */}
                    <div className="flex items-center space-x-4 text-xs text-gray-500">
                      <span>Model: {message.model}</span>
                      {message.id && <span>ID: {message.id}</span>}
                    </div>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
