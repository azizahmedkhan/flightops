import Link from 'next/link'
import { 
  Plane, 
  MessageSquare, 
  Search, 
  Database, 
  Activity,
  ArrowRight,
  Zap,
  Users
} from 'lucide-react'

export default function HomePage() {
  const features = [
    {
      title: 'Flight Query',
      description: 'Ask questions about flight disruptions and get AI-powered insights',
      icon: Plane,
      href: '/query',
      color: 'bg-black'
    },
    {
      title: 'Predictive Analytics',
      description: 'AI-powered disruption prediction and proactive management',
      icon: Zap,
      href: '/predictive',
      color: 'bg-blue-600'
    },
    {
      title: 'Crew Management',
      description: 'Intelligent crew optimization and resource management',
      icon: Users,
      href: '/crew',
      color: 'bg-green-600'
    },
    {
      title: 'Draft Communications',
      description: 'Generate empathetic customer communications with policy grounding',
      icon: MessageSquare,
      href: '/comms',
      color: 'bg-gray-800'
    },
    {
      title: 'Knowledge Search',
      description: 'Search through policies and procedures with semantic search',
      icon: Search,
      href: '/search',
      color: 'bg-gray-700'
    },
    {
      title: 'Data Management',
      description: 'Manage flight data, bookings, and crew rosters',
      icon: Database,
      href: '/data',
      color: 'bg-gray-600'
    },
    {
      title: 'System Monitoring',
      description: 'Monitor service health and performance metrics',
      icon: Activity,
      href: '/monitoring',
      color: 'bg-gray-500'
    },
    {
      title: 'Customer Communication',
      description: 'Test customer chat, email, and SMS communication',
      icon: MessageSquare,
      href: '/customer-chat',
      color: 'bg-black'
    }
  ]

  return (
    <div className="min-h-screen relative">
      {/* Header */}
      <header className="bg-black text-white relative z-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center space-x-3">
              <div className="bg-white p-2 rounded-lg">
                <Zap className="h-6 w-6 text-black" />
              </div>
              <div>
                <h1 className="text-2xl font-bold">Air New Zealand FlightOps</h1>
                <p className="text-sm text-gray-300">Intelligent Flight Operations Management</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <Link 
                href="/monitoring"
                className="text-sm text-white hover:text-gray-300 font-medium transition-colors"
              >
                System Status
              </Link>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 relative z-10">
        {/* Hero Section */}
        <div className="text-center mb-16">
          <h2 className="text-4xl font-bold text-black mb-4">
            Intelligent Flight Operations
          </h2>
          <p className="text-xl text-gray-700 max-w-3xl mx-auto font-medium">
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
                className="group bg-white/95 backdrop-blur-sm rounded-xl shadow-lg hover:shadow-xl transition-all duration-200 p-6 border-2 border-gray-200 hover:border-black"
              >
                <div className="flex items-start space-x-4">
                  <div className={`${feature.color} p-3 rounded-lg group-hover:scale-110 transition-transform duration-200`}>
                    <Icon className="h-6 w-6 text-white" />
                  </div>
                  <div className="flex-1">
                    <h3 className="text-lg font-bold text-black mb-2 group-hover:text-gray-600 transition-colors">
                      {feature.title}
                    </h3>
                    <p className="text-gray-600 text-sm mb-4 font-medium">
                      {feature.description}
                    </p>
                    <div className="flex items-center text-black text-sm font-semibold group-hover:translate-x-1 transition-transform">
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
        <div className="mt-16 bg-white/95 backdrop-blur-sm rounded-xl shadow-lg p-8 border-2 border-gray-200">
          <h3 className="text-xl font-bold text-black mb-6">Quick Actions</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Link
              href="/query?flight=NZ123&date=2025-09-17"
              className="flex items-center justify-center px-4 py-3 bg-black/10 text-black rounded-lg hover:bg-black/20 transition-colors font-semibold"
            >
              <Plane className="h-4 w-4 mr-2" />
              Check NZ123 Status
            </Link>
            <Link
              href="/comms?flight=NZ123&date=2025-09-17"
              className="flex items-center justify-center px-4 py-3 bg-gray-800/10 text-gray-800 rounded-lg hover:bg-gray-800/20 transition-colors font-semibold"
            >
              <MessageSquare className="h-4 w-4 mr-2" />
              Draft Customer Message
            </Link>
            <Link
              href="/data"
              className="flex items-center justify-center px-4 py-3 bg-gray-600/10 text-gray-600 rounded-lg hover:bg-gray-600/20 transition-colors font-semibold"
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
