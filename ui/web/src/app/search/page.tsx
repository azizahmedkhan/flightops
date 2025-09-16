'use client'

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'react-hot-toast'
import { 
  Search, 
  FileText, 
  Loader2, 
  ExternalLink,
  Star,
  Clock,
  Database
} from 'lucide-react'

const searchSchema = z.object({
  query: z.string().min(1, 'Search query is required'),
  limit: z.number().min(1).max(20).default(5)
})

type SearchForm = z.infer<typeof searchSchema>

interface SearchResult {
  doc_id: number
  title: string
  snippet: string
  meta: Record<string, any>
  score?: number
}

interface SearchResponse {
  mode: 'vector' | 'keyword'
  results: SearchResult[]
}

export default function SearchPage() {
  const [response, setResponse] = useState<SearchResponse | null>(null)
  const [loading, setLoading] = useState(false)

  const { register, handleSubmit, formState: { errors }, watch } = useForm<SearchForm>({
    resolver: zodResolver(searchSchema),
    defaultValues: {
      query: '',
      limit: 5
    }
  })

  const onSubmit = async (data: SearchForm) => {
    setLoading(true)
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_GATEWAY_URL || 'http://localhost:8080'}/search`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          q: data.query,
          k: data.limit
        })
      })

      if (!res.ok) {
        throw new Error('Failed to search')
      }

      const result = await res.json()
      setResponse(result)
      toast.success(`Found ${result.results.length} results`)
    } catch (error) {
      toast.error('Failed to search. Please try again.')
      console.error('Search error:', error)
    } finally {
      setLoading(false)
    }
  }

  const getScoreColor = (score?: number) => {
    if (!score) return 'text-gray-500'
    if (score > 0.8) return 'text-green-600'
    if (score > 0.6) return 'text-yellow-600'
    return 'text-red-600'
  }

  const getScoreLabel = (score?: number) => {
    if (!score) return 'N/A'
    if (score > 0.8) return 'Excellent'
    if (score > 0.6) return 'Good'
    if (score > 0.4) return 'Fair'
    return 'Poor'
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between py-6">
            <div className="flex items-center space-x-3">
              <Search className="h-8 w-8 text-purple-600" />
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Knowledge Search</h1>
                <p className="text-sm text-gray-600">Search through policies and procedures</p>
              </div>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Search Form */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200 sticky top-8">
              <h2 className="text-lg font-semibold text-gray-900 mb-6">Search Parameters</h2>
              
              <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Search Query
                  </label>
                  <textarea
                    {...register('query')}
                    rows={3}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                    placeholder="Search for policies, procedures, or guidelines..."
                  />
                  {errors.query && (
                    <p className="mt-1 text-sm text-red-600">{errors.query.message}</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Number of Results
                  </label>
                  <select
                    {...register('limit', { valueAsNumber: true })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  >
                    <option value={3}>3 results</option>
                    <option value={5}>5 results</option>
                    <option value={10}>10 results</option>
                    <option value={15}>15 results</option>
                    <option value={20}>20 results</option>
                  </select>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-purple-600 text-white py-2 px-4 rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
                >
                  {loading ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Searching...
                    </>
                  ) : (
                    <>
                      <Search className="h-4 w-4 mr-2" />
                      Search
                    </>
                  )}
                </button>
              </form>

              {/* Search Tips */}
              <div className="mt-8 p-4 bg-blue-50 rounded-lg">
                <h3 className="text-sm font-medium text-blue-900 mb-2">Search Tips</h3>
                <ul className="text-xs text-blue-700 space-y-1">
                  <li>• Use specific keywords for better results</li>
                  <li>• Try different phrasings if no results</li>
                  <li>• Search supports both vector and keyword matching</li>
                  <li>• Results are ranked by relevance score</li>
                </ul>
              </div>
            </div>
          </div>

          {/* Results */}
          <div className="lg:col-span-2">
            {response && (
              <div className="space-y-6">
                {/* Search Info */}
                <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-lg font-semibold text-gray-900">Search Results</h2>
                    <div className="flex items-center space-x-4 text-sm text-gray-600">
                      <div className="flex items-center">
                        <Database className="h-4 w-4 mr-1" />
                        {response.mode === 'vector' ? 'Vector Search' : 'Keyword Search'}
                      </div>
                      <div className="flex items-center">
                        <FileText className="h-4 w-4 mr-1" />
                        {response.results.length} results
                      </div>
                    </div>
                  </div>
                  
                  {response.results.length === 0 ? (
                    <div className="text-center py-8">
                      <Search className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                      <p className="text-gray-500">No results found for your search query</p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {response.results.map((result, index) => (
                        <div key={result.doc_id} className="border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow">
                          <div className="flex items-start justify-between mb-3">
                            <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                              <FileText className="h-5 w-5 mr-2 text-purple-600" />
                              {result.title}
                            </h3>
                            {result.score && (
                              <div className="flex items-center space-x-2">
                                <div className={`text-sm font-medium ${getScoreColor(result.score)}`}>
                                  {getScoreLabel(result.score)}
                                </div>
                                <div className="text-xs text-gray-500">
                                  {(result.score * 100).toFixed(1)}%
                                </div>
                              </div>
                            )}
                          </div>
                          
                          <p className="text-gray-700 mb-4 leading-relaxed">
                            {result.snippet}
                          </p>
                          
                          <div className="flex items-center justify-between">
                            <div className="flex items-center space-x-4 text-sm text-gray-500">
                              <div className="flex items-center">
                                <Clock className="h-4 w-4 mr-1" />
                                Document ID: {result.doc_id}
                              </div>
                              {result.meta?.source && (
                                <div className="flex items-center">
                                  <ExternalLink className="h-4 w-4 mr-1" />
                                  {result.meta.source}
                                </div>
                              )}
                            </div>
                            
                            {result.score && (
                              <div className="flex items-center">
                                <Star className={`h-4 w-4 mr-1 ${getScoreColor(result.score)}`} />
                                <span className={`text-sm font-medium ${getScoreColor(result.score)}`}>
                                  {result.score.toFixed(3)}
                                </span>
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {!response && (
              <div className="bg-white rounded-xl shadow-sm p-12 border border-gray-200 text-center">
                <Search className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-500">Enter a search query to find relevant documents</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
