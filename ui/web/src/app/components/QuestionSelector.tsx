'use client'

import { useState } from 'react'
import { 
  ChevronDown, 
  ChevronUp, 
  Search, 
  Plane, 
  Users, 
  MessageSquare, 
  DollarSign,
  AlertTriangle,
  Clock,
  CheckCircle
} from 'lucide-react'

interface Question {
  id: string
  text: string
  category: string
  icon: any
  description: string
}

const questions: Question[] = [
  // Flight Impact Questions
  {
    id: 'impact-basic',
    text: 'What is the impact of the delay on [flight_number] on [date]?',
    category: 'Flight Impact',
    icon: Plane,
    description: 'Get comprehensive impact assessment including passengers, crew, and aircraft status'
  },
  {
    id: 'passengers-count',
    text: 'How many passengers are affected by the disruption on [flight_number]?',
    category: 'Flight Impact',
    icon: Users,
    description: 'Get passenger count and connection details'
  },
  {
    id: 'crew-impact',
    text: 'What is the crew impact for [flight_number] on [date]?',
    category: 'Flight Impact',
    icon: Users,
    description: 'Get crew details, roles, and duty hours'
  },
  {
    id: 'flight-status',
    text: 'What is the current status of [flight_number] on [date]?',
    category: 'Flight Impact',
    icon: CheckCircle,
    description: 'Get current flight status and schedule information'
  },

  // Rebooking Questions
  {
    id: 'rebooking-options',
    text: 'What are the rebooking options for [flight_number] on [date]?',
    category: 'Rebooking & Recovery',
    icon: Plane,
    description: 'Get detailed rebooking strategies and cost analysis'
  },
  {
    id: 'recovery-time',
    text: 'What is the estimated recovery time for [flight_number]?',
    category: 'Rebooking & Recovery',
    icon: Clock,
    description: 'Get recovery time estimates and implementation plans'
  },
  {
    id: 'compensation-options',
    text: 'What compensation options are available for [flight_number] passengers?',
    category: 'Rebooking & Recovery',
    icon: DollarSign,
    description: 'Get compensation options based on policy and passenger impact'
  },

  // Communication Questions
  {
    id: 'draft-comms',
    text: 'Draft email and SMS notifications for [flight_number] passengers',
    category: 'Communication',
    icon: MessageSquare,
    description: 'Generate customer communications with policy grounding'
  },
  {
    id: 'passenger-update',
    text: 'What should we tell passengers about the delay on [flight_number]?',
    category: 'Communication',
    icon: MessageSquare,
    description: 'Get recommended messaging for passenger updates'
  },

  // Policy Questions
  {
    id: 'weather-policy',
    text: 'What is our policy for weather-related delays on [flight_number]?',
    category: 'Policy & Compliance',
    icon: AlertTriangle,
    description: 'Get policy guidance for weather-related disruptions'
  },
  {
    id: 'compensation-policy',
    text: 'What compensation is required for [flight_number] passengers?',
    category: 'Policy & Compliance',
    icon: DollarSign,
    description: 'Get compensation requirements based on policy'
  }
]

interface QuestionSelectorProps {
  onQuestionSelect: (question: string) => void
  flightNo: string
  date: string
}

export default function QuestionSelector({ onQuestionSelect, flightNo, date }: QuestionSelectorProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string>('All')

  const categories = ['All', ...Array.from(new Set(questions.map(q => q.category)))]

  const filteredQuestions = questions.filter(question => {
    const matchesSearch = question.text.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         question.description.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesCategory = selectedCategory === 'All' || question.category === selectedCategory
    return matchesSearch && matchesCategory
  })

  const handleQuestionSelect = (question: Question) => {
    const processedQuestion = question.text
      .replace('[flight_number]', flightNo)
      .replace('[date]', date)
    onQuestionSelect(processedQuestion)
    setIsOpen(false)
    setSearchTerm('')
  }

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-black focus:border-transparent transition-colors text-left flex items-center justify-between bg-white"
      >
        <span className="text-gray-700 font-medium">
          {isOpen ? 'Select a question...' : 'Choose from common questions'}
        </span>
        {isOpen ? (
          <ChevronUp className="h-5 w-5 text-gray-500" />
        ) : (
          <ChevronDown className="h-5 w-5 text-gray-500" />
        )}
      </button>

      {isOpen && (
        <div className="absolute top-full left-0 right-0 mt-2 bg-white border-2 border-gray-200 rounded-lg shadow-lg z-50 max-h-96 overflow-hidden">
          {/* Search and Filter */}
          <div className="p-4 border-b border-gray-200">
            <div className="relative mb-3">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search questions..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-black focus:border-transparent"
              />
            </div>
            
            <div className="flex flex-wrap gap-2">
              {categories.map(category => (
                <button
                  key={category}
                  onClick={() => setSelectedCategory(category)}
                  className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                    selectedCategory === category
                      ? 'bg-black text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {category}
                </button>
              ))}
            </div>
          </div>

          {/* Questions List */}
          <div className="max-h-64 overflow-y-auto">
            {filteredQuestions.length === 0 ? (
              <div className="p-4 text-center text-gray-500">
                No questions found matching your search
              </div>
            ) : (
              filteredQuestions.map(question => {
                const Icon = question.icon
                return (
                  <button
                    key={question.id}
                    onClick={() => handleQuestionSelect(question)}
                    className="w-full p-4 text-left hover:bg-gray-50 border-b border-gray-100 last:border-b-0 transition-colors"
                  >
                    <div className="flex items-start space-x-3">
                      <div className="bg-gray-100 p-2 rounded-lg">
                        <Icon className="h-4 w-4 text-gray-600" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 mb-1">
                          {question.text.replace('[flight_number]', flightNo).replace('[date]', date)}
                        </p>
                        <p className="text-xs text-gray-500 mb-1">
                          {question.description}
                        </p>
                        <span className="inline-block px-2 py-1 bg-gray-100 text-xs text-gray-600 rounded-full">
                          {question.category}
                        </span>
                      </div>
                    </div>
                  </button>
                )
              })
            )}
          </div>
        </div>
      )}
    </div>
  )
}
