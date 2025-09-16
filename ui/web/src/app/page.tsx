import Link from 'next/link'
import { 
  Plane, 
  MessageSquare, 
  Search, 
  Database, 
  Activity,
  ArrowRight,
  Zap
} from 'lucide-react'

export default function HomePage() {
  const features = [
    {
      title: 'Flight Query',
      description: 'Ask questions about flight disruptions and get AI-powered insights',
      icon: Plane,
      href: '/query',
      color: 'bg-blue-500'
    },
    {
      title: 'Draft Communications',
      description: 'Generate empathetic customer communications with policy grounding',
      icon: MessageSquare,
      href: '/comms',
      color: 'bg-green-500'
    },
    {
      title: 'Knowledge Search',
      description: 'Search through policies and procedures with semantic search',
      icon: Search,
      href: '/search',
      color: 'bg-purple-500'
    },
    {
      title: 'Data Management',
      description: 'Manage flight data, bookings, and crew rosters',
      icon: Database,
      href: '/data',
      color: 'bg-orange-500'
    },
    {
      title: 'System Monitoring',
      description: 'Monitor service health and performance metrics',
      icon: Activity,
      href: '/monitoring',
      color: 'bg-red-500'
    },
    {
      title: 'Customer Communication',
      description: 'Test customer chat, email, and SMS communication',
      icon: MessageSquare,
      href: '/customer-chat',
      color: 'bg-indigo-500'
    }
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center space-x-3">
              <div className="bg-blue-600 p-2 rounded-lg">
                <Zap className="h-6 w-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">FlightOps Copilot</h1>
                <p className="text-sm text-gray-600">RAG + Agents + Guardrails + Observability</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <Link 
                href="/monitoring"
                className="text-sm text-gray-600 hover:text-gray-900"
              >
                System Status
              </Link>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Hero Section */}
        <div className="text-center mb-16">
          <h2 className="text-4xl font-bold text-gray-900 mb-4">
            Intelligent Flight Operations
          </h2>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Leverage AI-powered agents to handle flight disruptions, draft customer communications, 
            and maintain operational excellence with grounded policy knowledge.
          </p>
        </div>

        {/* Features Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {features.map((feature) => {
            const Icon = feature.icon
            return (
              <Link
                key={feature.title}
                href={feature.href}
                className="group bg-white rounded-xl shadow-sm hover:shadow-md transition-all duration-200 p-6 border border-gray-200 hover:border-gray-300"
              >
                <div className="flex items-start space-x-4">
                  <div className={`${feature.color} p-3 rounded-lg group-hover:scale-110 transition-transform duration-200`}>
                    <Icon className="h-6 w-6 text-white" />
                  </div>
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-gray-900 mb-2 group-hover:text-blue-600 transition-colors">
                      {feature.title}
                    </h3>
                    <p className="text-gray-600 text-sm mb-4">
                      {feature.description}
                    </p>
                    <div className="flex items-center text-blue-600 text-sm font-medium group-hover:translate-x-1 transition-transform">
                      Get started
                      <ArrowRight className="h-4 w-4 ml-1" />
                    </div>
                  </div>
                </div>
              </Link>
            )
          })}
        </div>

        {/* Quick Actions */}
        <div className="mt-16 bg-white rounded-xl shadow-sm p-8 border border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-6">Quick Actions</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Link
              href="/query?flight=NZ123&date=2025-09-17"
              className="flex items-center justify-center px-4 py-3 bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100 transition-colors"
            >
              <Plane className="h-4 w-4 mr-2" />
              Check NZ123 Status
            </Link>
            <Link
              href="/comms?flight=NZ123&date=2025-09-17"
              className="flex items-center justify-center px-4 py-3 bg-green-50 text-green-700 rounded-lg hover:bg-green-100 transition-colors"
            >
              <MessageSquare className="h-4 w-4 mr-2" />
              Draft Customer Message
            </Link>
            <Link
              href="/data"
              className="flex items-center justify-center px-4 py-3 bg-orange-50 text-orange-700 rounded-lg hover:bg-orange-100 transition-colors"
            >
              <Database className="h-4 w-4 mr-2" />
              Seed Demo Data
            </Link>
          </div>
        </div>
      </main>
    </div>
  )
}
