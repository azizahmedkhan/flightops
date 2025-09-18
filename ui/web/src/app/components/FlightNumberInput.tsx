'use client'

import { useState, useEffect, useRef } from 'react'
import { 
  ChevronDown, 
  ChevronUp, 
  Search, 
  Plane, 
  Clock,
  CheckCircle,
  AlertTriangle,
  XCircle
} from 'lucide-react'

interface FlightSuggestion {
  flight_no: string
  flight_date: string
  route: string
  status: string
  display: string
}

interface FlightNumberInputProps {
  value: string
  onChange: (value: string) => void
  onSelect?: (suggestion: FlightSuggestion) => void
  placeholder?: string
  className?: string
  disabled?: boolean
  error?: string
}

const statusIcons = {
  'ON_TIME': CheckCircle,
  'DELAYED': Clock,
  'CANCELLED': XCircle,
  'DIVERTED': AlertTriangle,
  'BOARDING': Clock,
  'DEPARTED': CheckCircle,
  'ARRIVED': CheckCircle
}

const statusColors = {
  'ON_TIME': 'text-green-600',
  'DELAYED': 'text-yellow-600',
  'CANCELLED': 'text-red-600',
  'DIVERTED': 'text-orange-600',
  'BOARDING': 'text-blue-600',
  'DEPARTED': 'text-green-600',
  'ARRIVED': 'text-green-600'
}

export default function FlightNumberInput({ 
  value, 
  onChange, 
  onSelect,
  placeholder = "Enter flight number (e.g., NZ123)",
  className = "",
  disabled = false,
  error
}: FlightNumberInputProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [suggestions, setSuggestions] = useState<FlightSuggestion[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedIndex, setSelectedIndex] = useState(-1)
  const inputRef = useRef<HTMLInputElement>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const debounceRef = useRef<NodeJS.Timeout>()

  // Debounced search function
  const searchFlights = async (query: string) => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current)
    }

    debounceRef.current = setTimeout(async () => {
      if (query.length < 1) {
        setSuggestions([])
        return
      }

      setLoading(true)
      try {
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_GATEWAY_URL || 'http://localhost:8080'}/flights/autocomplete?q=${encodeURIComponent(query)}&limit=10`
        )
        
        if (response.ok) {
          const data = await response.json()
          setSuggestions(data.suggestions || [])
        } else {
          setSuggestions([])
        }
      } catch (error) {
        console.error('Error fetching flight suggestions:', error)
        setSuggestions([])
      } finally {
        setLoading(false)
      }
    }, 300) // 300ms debounce
  }

  // Handle input change
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value
    onChange(newValue)
    searchFlights(newValue)
    setSelectedIndex(-1)
    
    if (newValue.length > 0) {
      setIsOpen(true)
    } else {
      setIsOpen(false)
    }
  }

  // Handle suggestion selection
  const handleSuggestionSelect = (suggestion: FlightSuggestion) => {
    onChange(suggestion.flight_no)
    if (onSelect) {
      onSelect(suggestion)
    }
    setIsOpen(false)
    setSelectedIndex(-1)
  }

  // Handle keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen || suggestions.length === 0) return

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        setSelectedIndex(prev => 
          prev < suggestions.length - 1 ? prev + 1 : prev
        )
        break
      case 'ArrowUp':
        e.preventDefault()
        setSelectedIndex(prev => prev > 0 ? prev - 1 : -1)
        break
      case 'Enter':
        e.preventDefault()
        if (selectedIndex >= 0 && selectedIndex < suggestions.length) {
          handleSuggestionSelect(suggestions[selectedIndex])
        }
        break
      case 'Escape':
        setIsOpen(false)
        setSelectedIndex(-1)
        break
    }
  }

  // Handle click outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current && 
        !dropdownRef.current.contains(event.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false)
        setSelectedIndex(-1)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Focus input when component mounts
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.focus()
    }
  }, [])

  return (
    <div className="relative">
      <div className="relative">
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onFocus={() => {
            if (value.length > 0) {
              setIsOpen(true)
            }
          }}
          placeholder={placeholder}
          disabled={disabled}
          className={`w-full px-4 py-3 pr-10 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-black focus:border-transparent transition-colors ${error ? 'border-red-500' : ''} ${className}`}
        />
        <div className="absolute inset-y-0 right-0 flex items-center pr-3">
          {loading ? (
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600"></div>
          ) : (
            <Search className="h-4 w-4 text-gray-400" />
          )}
        </div>
      </div>

      {error && (
        <p className="mt-1 text-sm text-red-600 font-medium">{error}</p>
      )}

      {isOpen && (suggestions.length > 0 || loading) && (
        <div
          ref={dropdownRef}
          className="absolute top-full left-0 right-0 mt-2 bg-white border-2 border-gray-200 rounded-lg shadow-lg z-50 max-h-64 overflow-y-auto"
        >
          {loading ? (
            <div className="p-4 text-center text-gray-500">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-gray-600 mx-auto"></div>
              <p className="mt-2 text-sm">Searching flights...</p>
            </div>
          ) : suggestions.length === 0 ? (
            <div className="p-4 text-center text-gray-500">
              <Plane className="h-6 w-6 mx-auto mb-2 text-gray-400" />
              <p className="text-sm">No flights found</p>
            </div>
          ) : (
            <div className="py-2">
              {suggestions.map((suggestion, index) => {
                const StatusIcon = statusIcons[suggestion.status as keyof typeof statusIcons] || Clock
                const statusColor = statusColors[suggestion.status as keyof typeof statusColors] || 'text-gray-600'
                
                return (
                  <button
                    key={`${suggestion.flight_no}-${suggestion.flight_date}`}
                    onClick={() => handleSuggestionSelect(suggestion)}
                    className={`w-full px-4 py-3 text-left hover:bg-gray-50 border-b border-gray-100 last:border-b-0 transition-colors ${
                      index === selectedIndex ? 'bg-gray-100' : ''
                    }`}
                  >
                    <div className="flex items-center space-x-3">
                      <div className="bg-gray-100 p-2 rounded-lg">
                        <StatusIcon className={`h-4 w-4 ${statusColor}`} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2">
                          <p className="text-sm font-medium text-gray-900">
                            {suggestion.flight_no}
                          </p>
                          <span className={`text-xs font-medium px-2 py-1 rounded-full ${statusColor} bg-gray-100`}>
                            {suggestion.status}
                          </span>
                        </div>
                        <p className="text-xs text-gray-500 mt-1">
                          {suggestion.route} • {suggestion.flight_date}
                        </p>
                      </div>
                    </div>
                  </button>
                )
              })}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
