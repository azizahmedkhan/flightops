'use client'

import { useState } from 'react'
import Link from 'next/link'
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
  mode: string
  results: SearchResult[]
  embeddingsAvailable?: boolean
  categoryCounts?: Record<string, number>
  totalDocuments?: number
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
          query: data.query,
          k: data.limit
        })
      })

      if (!res.ok) {
        throw new Error('Failed to search')
      }

      const rawResult = await res.json()

      if (!Array.isArray(rawResult?.results)) {
        console.error('Unexpected search response payload:', rawResult)
        throw new Error('Unexpected search response payload')
      }

      const normalizedResults: SearchResult[] = rawResult.results.map((item: any, index: number) => {
        const rawDocId = typeof item.doc_id === 'number' ? item.doc_id : Number(item.doc_id)
        const docId = Number.isFinite(rawDocId) ? rawDocId : index

        return {
          doc_id: docId,
          title: typeof item.title === 'string' ? item.title : 'Untitled Document',
          snippet: typeof item.snippet === 'string'
            ? item.snippet
            : typeof item.content === 'string'
              ? item.content
              : '',
          meta: typeof item.meta === 'object' && item.meta !== null ? item.meta : {},
          score: typeof item.score === 'number' ? item.score : undefined
        }
      })

      const normalizedResponse: SearchResponse = {
        mode: typeof rawResult.mode === 'string' ? rawResult.mode : 'unknown',
        results: normalizedResults,
        embeddingsAvailable: typeof rawResult.embeddings_available === 'boolean'
          ? rawResult.embeddings_available
          : undefined,
        categoryCounts: rawResult.category_counts ?? undefined,
        totalDocuments: typeof rawResult.total_documents === 'number'
          ? rawResult.total_documents
          : undefined
      }

      setResponse(normalizedResponse)
      toast.success(`Found ${normalizedResponse.results.length} results`)
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

  const getModeLabel = (mode: string) => {
    switch (mode) {
      case 'vector':
        return 'Vector Search'
      case 'keyword':
        return 'Keyword Search'
      case 'hybrid':
        return 'Hybrid Search'
      case 'bm25_only':
        return 'Keyword Search (BM25)'
      case 'no_data':
        return 'Knowledge Base Unavailable'
      default:
        return 'Search'
    }
  }

  return (
    <div className="min-h-screen relative">
      {/* Header */}
      <header className="bg-black text-white relative z-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between py-6">
            <div className="flex items-center space-x-3">
              <div className="bg-white p-2 rounded-lg">
                <Search className="h-6 w-6 text-black" />
              </div>
              <div>
                <h1 className="text-2xl font-bold">Knowledge Search</h1>
                <p className="text-sm text-gray-300">Search through policies and procedures</p>
              </div>
            </div>
            <Link href="/" className="text-sm font-medium text-white hover:text-gray-200">
              Back to Home
            </Link>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 relative z-10">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Search Form */}
          <div className="lg:col-span-1">
            <div className="bg-white/95 backdrop-blur-sm rounded-xl shadow-lg p-6 border-2 border-gray-200 sticky top-8">
              <h2 className="text-xl font-bold text-black mb-6">Search Parameters</h2>
              
              <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
                <div>
                  <label className="block text-sm font-semibold text-gray-900 mb-2">
                    Search Query
                  </label>
                  <textarea
                    {...register('query')}
                    rows={3}
                    className="w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-black focus:border-transparent transition-colors"
                    placeholder="Search for policies, procedures, or guidelines..."
                  />
                  {errors.query && (
                    <p className="mt-1 text-sm text-red-600 font-medium">{errors.query.message}</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-semibold text-gray-900 mb-2">
                    Number of Results
                  </label>
                  <select
                    {...register('limit', { valueAsNumber: true })}
                    className="w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-black focus:border-transparent transition-colors"
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
                  className="w-full bg-black text-white py-3 px-6 rounded-lg hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center font-semibold transition-colors"
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
              <div className="mt-8 p-4 bg-gray-100 rounded-lg border-2 border-gray-200">
                <h3 className="text-sm font-semibold text-black mb-2">Search Tips</h3>
                <ul className="text-xs text-gray-700 space-y-1 font-medium">
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
                <div className="bg-white/95 backdrop-blur-sm rounded-xl shadow-lg p-6 border-2 border-gray-200">
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-xl font-bold text-black">Search Results</h2>
                    <div className="flex items-center space-x-4 text-sm text-gray-600">
                      <div className="flex items-center">
                        <Database className="h-4 w-4 mr-1" />
                        {getModeLabel(response.mode)}
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
                        <div key={result.doc_id} className="bg-white/95 backdrop-blur-sm border-2 border-gray-200 rounded-lg p-6 hover:shadow-lg transition-all duration-200">
                          <div className="flex items-start justify-between mb-3">
                            <h3 className="text-lg font-bold text-black flex items-center">
                              <div className="bg-black p-2 rounded-lg mr-3">
                                <FileText className="h-5 w-5 text-white" />
                              </div>
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
              <div className="bg-white/95 backdrop-blur-sm rounded-xl shadow-lg p-12 border-2 border-gray-200 text-center">
                <div className="bg-black p-4 rounded-full w-16 h-16 mx-auto mb-4 flex items-center justify-center">
                  <Search className="h-8 w-8 text-white" />
                </div>
                <p className="text-gray-600 font-semibold">Enter a search query to find relevant documents</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
