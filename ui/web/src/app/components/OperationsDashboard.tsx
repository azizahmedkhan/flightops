'use client'

import { motion } from 'framer-motion'
import { useEffect, useState } from 'react'
import { 
  Plane, 
  CheckCircle, 
  Clock, 
  AlertTriangle,
  TrendingUp,
  Users,
  MapPin
} from 'lucide-react'

interface Operation {
  id: string
  type: 'departure' | 'arrival' | 'delay' | 'on-time'
  flight: string
  route: string
  status: string
  time: string
  progress: number
}

export default function OperationsDashboard() {
  const [operations, setOperations] = useState<Operation[]>([])

  useEffect(() => {
    // Initialize with some operations
    const initialOps: Operation[] = [
      {
        id: '1',
        type: 'departure',
        flight: 'AA128',
        route: 'NYC → LAX',
        status: 'Boarding',
        time: '14:30',
        progress: 75
      },
      {
        id: '2',
        type: 'on-time',
        flight: 'UA245',
        route: 'SFO → MIA',
        status: 'On Schedule',
        time: '15:45',
        progress: 100
      },
      {
        id: '3',
        type: 'arrival',
        flight: 'DL789',
        route: 'ATL → NYC',
        status: 'Landed',
        time: '13:20',
        progress: 100
      },
      {
        id: '4',
        type: 'delay',
        flight: 'SW412',
        route: 'DEN → CHI',
        status: 'Delayed',
        time: '16:15',
        progress: 45
      }
    ]
    setOperations(initialOps)

    // Simulate real-time updates
    const interval = setInterval(() => {
      setOperations(prev => prev.map(op => ({
        ...op,
        progress: op.type === 'delay' 
          ? Math.max(20, op.progress - Math.random() * 5)
          : Math.min(100, op.progress + Math.random() * 3),
        time: op.type === 'arrival' 
          ? op.time 
          : new Date(Date.now() + Math.random() * 60000).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
      })))
    }, 2000)

    return () => clearInterval(interval)
  }, [])

  const getStatusColor = (type: string) => {
    switch(type) {
      case 'on-time':
      case 'arrival':
        return 'text-green-600 bg-green-50 border-green-200'
      case 'delay':
        return 'text-orange-600 bg-orange-50 border-orange-200'
      case 'departure':
        return 'text-blue-600 bg-blue-50 border-blue-200'
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200'
    }
  }

  const getStatusIcon = (type: string) => {
    switch(type) {
      case 'on-time':
      case 'arrival':
        return <CheckCircle className="h-4 w-4" />
      case 'delay':
        return <AlertTriangle className="h-4 w-4" />
      case 'departure':
        return <Plane className="h-4 w-4" />
      default:
        return <Clock className="h-4 w-4" />
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.8 }}
      viewport={{ once: true }}
      className="glass-liquid rounded-3xl p-8 shadow-2xl relative overflow-hidden"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h3 className="text-2xl font-bold bg-gradient-to-r from-blue-600 via-slate-600 to-gray-700 bg-clip-text text-transparent">
            Live Operations Center
          </h3>
          <p className="text-sm text-gray-600 mt-1">Real-time flight monitoring</p>
        </div>
        <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-green-100 border border-green-200">
          <motion.div
            animate={{ scale: [1, 1.2, 1] }}
            transition={{ duration: 2, repeat: Infinity }}
            className="w-2 h-2 bg-green-500 rounded-full"
          />
          <span className="text-xs font-semibold text-green-700">LIVE</span>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        {[
          { icon: TrendingUp, label: 'On-Time', value: '94.2%', color: 'text-green-600' },
          { icon: Plane, label: 'Active', value: '127', color: 'text-blue-600' },
          { icon: Users, label: 'Passengers', value: '18.5K', color: 'text-purple-600' },
          { icon: MapPin, label: 'Airports', value: '42', color: 'text-orange-600' }
        ].map((stat, idx) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, scale: 0.9 }}
            whileInView={{ opacity: 1, scale: 1 }}
            transition={{ delay: idx * 0.1, duration: 0.5 }}
            viewport={{ once: true }}
            className="glass-card rounded-2xl p-4 text-center"
          >
            <stat.icon className={`h-6 w-6 mx-auto mb-2 ${stat.color}`} />
            <div className="text-2xl font-bold text-gray-900">{stat.value}</div>
            <div className="text-xs text-gray-600">{stat.label}</div>
          </motion.div>
        ))}
      </div>

      {/* Operations List */}
      <div className="space-y-3">
        {operations.map((op, idx) => (
          <motion.div
            key={op.id}
            initial={{ opacity: 0, x: -20 }}
            whileInView={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.5 + idx * 0.1, duration: 0.5 }}
            viewport={{ once: true }}
            className={`glass-card rounded-xl p-4 border ${getStatusColor(op.type)} hover-glass cursor-pointer transition-all duration-300`}
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded-lg ${getStatusColor(op.type)}`}>
                  {getStatusIcon(op.type)}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-gray-900">{op.flight}</span>
                    <span className="text-xs text-gray-500">•</span>
                    <span className="text-sm text-gray-600">{op.route}</span>
                  </div>
                  <div className="text-xs text-gray-500 mt-0.5">{op.status}</div>
                </div>
              </div>
              <div className="text-right">
                <div className="text-sm font-semibold text-gray-900">{op.time}</div>
                <div className="text-xs text-gray-500">EST</div>
              </div>
            </div>
            
            {/* Progress Bar */}
            <div className="relative h-2 bg-gray-200 rounded-full overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${op.progress}%` }}
                transition={{ duration: 1, ease: "easeOut" }}
                className={`h-full rounded-full ${
                  op.type === 'delay' 
                    ? 'bg-gradient-to-r from-orange-500 to-orange-600'
                    : op.type === 'on-time' || op.type === 'arrival'
                    ? 'bg-gradient-to-r from-green-500 to-green-600'
                    : 'bg-gradient-to-r from-blue-500 to-blue-600'
                }`}
              />
            </div>
          </motion.div>
        ))}
      </div>

      {/* Animated Background Elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none -z-10">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
          className="absolute -top-20 -right-20 w-40 h-40 border border-blue-200/20 rounded-full"
        />
        <motion.div
          animate={{ rotate: -360 }}
          transition={{ duration: 30, repeat: Infinity, ease: "linear" }}
          className="absolute -bottom-20 -left-20 w-60 h-60 border border-slate-200/20 rounded-full"
        />
      </div>
    </motion.div>
  )
}

