'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { toast } from 'react-hot-toast'
import {
  Activity,
  CheckCircle,
  XCircle,
  AlertTriangle,
  RefreshCw,
  Server,
  Database,
  MessageSquare,
  MessageCircle,
  Search,
  Upload,
  Loader2,
  Cpu
} from 'lucide-react'

type IconType = typeof Activity

interface ServiceDefinition {
  key: string
  name: string
  port: number
  path: string
  icon: IconType
  cardClasses: string
  iconClass: string
  titleClass: string
  subtitleClass: string
}

interface ServiceStatus extends ServiceDefinition {
  status: 'healthy' | 'unhealthy' | 'checking'
  responseTime?: number
  lastChecked?: string
  error?: string
  endpoint: string
}

const GATEWAY_BASE = process.env.NEXT_PUBLIC_GATEWAY_URL || 'http://localhost:8080'

const GATEWAY_URL = (() => {
  try {
    return new URL(GATEWAY_BASE)
  } catch (error) {
    console.warn('Invalid NEXT_PUBLIC_GATEWAY_URL, defaulting to http://localhost:8080', error)
    return new URL('http://localhost:8080')
  }
})()

const DEFAULT_GATEWAY_PORT = GATEWAY_URL.port
  ? Number(GATEWAY_URL.port)
  : GATEWAY_URL.protocol === 'https:'
    ? 443
    : 80

const SERVICE_DEFINITIONS: ServiceDefinition[] = [
  {
    key: 'gateway',
    name: 'Gateway API',
    port: DEFAULT_GATEWAY_PORT,
    path: '/health',
    icon: Server,
    cardClasses: 'bg-indigo-50 border-indigo-200',
    iconClass: 'text-indigo-700',
    titleClass: 'text-indigo-900',
    subtitleClass: 'text-indigo-700'
  },
  {
    key: 'knowledge-engine',
    name: 'Knowledge Engine',
    port: 8081,
    path: '/health',
    icon: Search,
    cardClasses: 'bg-purple-50 border-purple-200',
    iconClass: 'text-purple-700',
    titleClass: 'text-purple-900',
    subtitleClass: 'text-purple-700'
  },
  {
    key: 'agent',
    name: 'Agent Service',
    port: 8082,
    path: '/health',
    icon: Activity,
    cardClasses: 'bg-green-50 border-green-200',
    iconClass: 'text-green-700',
    titleClass: 'text-green-900',
    subtitleClass: 'text-green-700'
  },
  {
    key: 'comms',
    name: 'Comms Service',
    port: 8083,
    path: '/health',
    icon: MessageSquare,
    cardClasses: 'bg-orange-50 border-orange-200',
    iconClass: 'text-orange-700',
    titleClass: 'text-orange-900',
    subtitleClass: 'text-orange-700'
  },
  {
    key: 'ingestion',
    name: 'Ingestion Worker',
    port: 8084,
    path: '/health',
    icon: Upload,
    cardClasses: 'bg-red-50 border-red-200',
    iconClass: 'text-red-700',
    titleClass: 'text-red-900',
    subtitleClass: 'text-red-700'
  },
  {
    key: 'customer-chat',
    name: 'Customer Chat',
    port: 8087,
    path: '/health',
    icon: MessageCircle,
    cardClasses: 'bg-pink-50 border-pink-200',
    iconClass: 'text-pink-700',
    titleClass: 'text-pink-900',
    subtitleClass: 'text-pink-700'
  },
  {
    key: 'scalable-chatbot',
    name: 'Scalable Chatbot',
    port: 8088,
    path: '/health',
    icon: Cpu,
    cardClasses: 'bg-teal-50 border-teal-200',
    iconClass: 'text-teal-700',
    titleClass: 'text-teal-900',
    subtitleClass: 'text-teal-700'
  },
  {
    key: 'db-router',
    name: 'DB Router',
    port: 8089,
    path: '/healthz',
    icon: Database,
    cardClasses: 'bg-yellow-50 border-yellow-200',
    iconClass: 'text-yellow-700',
    titleClass: 'text-yellow-900',
    subtitleClass: 'text-yellow-700'
  }
]

const buildEndpoint = (service: Pick<ServiceDefinition, 'path' | 'port'>) => {
  const url = new URL(service.path, GATEWAY_URL)
  url.port = String(service.port)
  return url.toString()
}

export default function MonitoringPage() {
  const [serviceHealth, setServiceHealth] = useState<ServiceStatus[]>(
    SERVICE_DEFINITIONS.map(service => ({
      ...service,
      status: 'checking',
      endpoint: buildEndpoint(service)
    }))
  )
  const [checking, setChecking] = useState(false)
  const [lastCheck, setLastCheck] = useState<Date | null>(null)

  const checkServiceHealth = async (service: ServiceStatus) => {
    const startTime = Date.now()
    const endpoint = buildEndpoint(service)
    try {
      const response = await fetch(endpoint, {
        method: 'GET',
        signal: AbortSignal.timeout(5000) // 5 second timeout
      })
      
      const responseTime = Date.now() - startTime
      
      if (response.ok) {
        return {
          ...service,
          status: 'healthy' as const,
          responseTime,
          lastChecked: new Date().toISOString(),
          error: undefined,
          endpoint
        }
      } else {
        return {
          ...service,
          status: 'unhealthy' as const,
          responseTime,
          lastChecked: new Date().toISOString(),
          error: `HTTP ${response.status}: ${response.statusText}`,
          endpoint
        }
      }
    } catch (error) {
      const responseTime = Date.now() - startTime
      return {
        ...service,
        status: 'unhealthy' as const,
        responseTime,
        lastChecked: new Date().toISOString(),
        error: error instanceof Error ? error.message : 'Unknown error',
        endpoint
      }
    }
  }

  const checkAllServices = async () => {
    setChecking(true)
    try {
      const healthChecks = await Promise.all(
        serviceHealth.map(service => checkServiceHealth(service))
      )
      setServiceHealth(healthChecks)
      setLastCheck(new Date())
      toast.success('Health check completed')
    } catch (error) {
      toast.error('Failed to check service health')
      console.error('Health check error:', error)
    } finally {
      setChecking(false)
    }
  }

  useEffect(() => {
    checkAllServices()
    // Set up automatic health checks every 30 seconds
    const interval = setInterval(checkAllServices, 30000)
    return () => clearInterval(interval)
  }, [])

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle className="h-5 w-5 text-green-600" />
      case 'unhealthy':
        return <XCircle className="h-5 w-5 text-red-600" />
      case 'checking':
        return <Loader2 className="h-5 w-5 text-yellow-600 animate-spin" />
      default:
        return <AlertTriangle className="h-5 w-5 text-gray-400" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'bg-green-50 border-green-200'
      case 'unhealthy':
        return 'bg-red-50 border-red-200'
      case 'checking':
        return 'bg-yellow-50 border-yellow-200'
      default:
        return 'bg-gray-50 border-gray-200'
    }
  }

  const healthyCount = serviceHealth.filter(s => s.status === 'healthy').length
  const totalCount = serviceHealth.length

  return (
    <div className="min-h-screen relative">
      {/* Header */}
      <header className="bg-black text-white relative z-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between py-6">
            <div className="flex items-center space-x-3">
              <div className="bg-white p-2 rounded-lg">
                <Activity className="h-6 w-6 text-black" />
              </div>
              <div>
                <h1 className="text-2xl font-bold">System Monitoring</h1>
                <p className="text-sm text-gray-300">Monitor service health and performance metrics</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <Link href="/" className="text-sm font-medium text-white hover:text-gray-200">
                Back to Home
              </Link>
              <button
                onClick={checkAllServices}
                disabled={checking}
                className="flex items-center px-4 py-2 text-sm text-white hover:text-gray-200 border-2 border-gray-300 rounded-lg hover:bg-gray-800 disabled:opacity-50 font-semibold transition-colors"
              >
                <RefreshCw className={`h-4 w-4 mr-2 ${checking ? 'animate-spin' : ''}`} />
                {checking ? 'Checking...' : 'Refresh'}
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 relative z-10">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Service Health */}
          <div className="lg:col-span-2 space-y-6">
            {/* Overview */}
            <div className="bg-white/95 backdrop-blur-sm rounded-xl shadow-lg p-6 border-2 border-gray-200">
              <h2 className="text-xl font-bold text-black mb-6">Service Overview</h2>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <div className="text-center p-4 bg-green-50 rounded-lg border-2 border-green-200">
                  <div className="text-2xl font-bold text-green-600">{healthyCount}</div>
                  <div className="text-sm text-green-600 font-semibold">Healthy</div>
                </div>
                <div className="text-center p-4 bg-red-50 rounded-lg border-2 border-red-200">
                  <div className="text-2xl font-bold text-red-600">{totalCount - healthyCount}</div>
                  <div className="text-sm text-red-600 font-semibold">Unhealthy</div>
                </div>
                <div className="text-center p-4 bg-blue-50 rounded-lg border-2 border-blue-200">
                  <div className="text-2xl font-bold text-blue-600">{totalCount}</div>
                  <div className="text-sm text-blue-600 font-semibold">Total</div>
                </div>
              </div>

              {lastCheck && (
                <p className="text-sm text-gray-500 text-center">
                  Last checked: {lastCheck.toLocaleString()}
                </p>
              )}
            </div>

            {/* Service Details */}
            <div className="bg-white/95 backdrop-blur-sm rounded-xl shadow-lg p-6 border-2 border-gray-200">
              <h2 className="text-xl font-bold text-black mb-6">Service Details</h2>
              
              <div className="space-y-4">
                {serviceHealth.map((service, index) => (
                  <div key={service.key} className={`p-4 rounded-lg border-2 ${getStatusColor(service.status)}`}>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center space-x-3">
                        {getStatusIcon(service.status)}
                        <h3 className="font-bold text-black">{service.name}</h3>
                      </div>
                      <div className="text-sm text-gray-500 font-semibold">
                        {service.responseTime && `${service.responseTime}ms`}
                      </div>
                    </div>

                    {service.error && (
                      <p className="text-sm text-red-600 mt-2">{service.error}</p>
                    )}

                    <p className="text-xs text-gray-500 mt-1 break-all">
                      Endpoint: {service.endpoint}
                    </p>

                    {service.lastChecked && (
                      <p className="text-xs text-gray-500 mt-1">
                        Last checked: {new Date(service.lastChecked).toLocaleString()}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Service Icons */}
            <div className="bg-white/95 backdrop-blur-sm rounded-xl shadow-lg p-6 border-2 border-gray-200">
              <h2 className="text-xl font-bold text-black mb-6">Services</h2>
              
              <div className="space-y-4">
                {serviceHealth.map(service => (
                  <div
                    key={`${service.key}-card`}
                    className={`flex items-center space-x-3 p-3 rounded-lg border-2 ${service.cardClasses}`}
                  >
                    <service.icon className={`h-5 w-5 ${service.iconClass}`} />
                    <div>
                      <p className={`font-bold ${service.titleClass}`}>{service.name}</p>
                      <p className={`text-sm font-semibold ${service.subtitleClass}`}>
                        Port {service.port}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Quick Actions */}
            <div className="bg-white/95 backdrop-blur-sm rounded-xl shadow-lg p-6 border-2 border-gray-200">
              <h2 className="text-xl font-bold text-black mb-6">Quick Actions</h2>
              
              <div className="space-y-3">
                <button 
                  onClick={checkAllServices}
                  disabled={checking}
                  className="w-full text-left p-3 text-sm text-gray-700 hover:bg-gray-100 rounded-lg border-2 border-gray-200 disabled:opacity-50 font-semibold transition-colors"
                >
                  <RefreshCw className={`h-4 w-4 mr-2 inline ${checking ? 'animate-spin' : ''}`} />
                  Refresh All Services
                </button>
                <button className="w-full text-left p-3 text-sm text-gray-700 hover:bg-gray-100 rounded-lg border-2 border-gray-200 font-semibold transition-colors">
                  View Detailed Logs
                </button>
                <button className="w-full text-left p-3 text-sm text-gray-700 hover:bg-gray-100 rounded-lg border-2 border-gray-200 font-semibold transition-colors">
                  Export Health Report
                </button>
                <button className="w-full text-left p-3 text-sm text-gray-700 hover:bg-gray-100 rounded-lg border-2 border-gray-200 font-semibold transition-colors">
                  Configure Alerts
                </button>
              </div>
            </div>

            {/* System Info */}
            <div className="bg-white/95 backdrop-blur-sm rounded-xl shadow-lg p-6 border-2 border-gray-200">
              <h2 className="text-xl font-bold text-black mb-6">System Info</h2>
              
              <div className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600 font-semibold">Environment:</span>
                  <span className="font-bold text-black">Development</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600 font-semibold">Version:</span>
                  <span className="font-bold text-black">1.0.0</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600 font-semibold">Uptime:</span>
                  <span className="font-bold text-black">N/A</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600 font-semibold">Last Deploy:</span>
                  <span className="font-bold text-black">N/A</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
