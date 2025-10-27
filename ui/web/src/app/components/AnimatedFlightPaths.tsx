'use client'

import { motion } from 'framer-motion'
import { useEffect, useState } from 'react'

interface FlightPath {
  id: number
  startX: number
  startY: number
  endX: number
  endY: number
  duration: number
  delay: number
}

export default function AnimatedFlightPaths() {
  const [flightPaths, setFlightPaths] = useState<FlightPath[]>([])

  useEffect(() => {
    const paths: FlightPath[] = []
    for (let i = 0; i < 8; i++) {
      paths.push({
        id: i,
        startX: Math.random() * 100,
        startY: Math.random() * 100,
        endX: Math.random() * 100,
        endY: Math.random() * 100,
        duration: 15 + Math.random() * 10,
        delay: Math.random() * 5
      })
    }
    setFlightPaths(paths)
  }, [])

  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none opacity-30">
      <svg className="w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
        <defs>
          <linearGradient id="flightGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#3B82F6" stopOpacity="0.6" />
            <stop offset="50%" stopColor="#6B7280" stopOpacity="0.4" />
            <stop offset="100%" stopColor="#06B6D4" stopOpacity="0.2" />
          </linearGradient>
        </defs>
        
        {flightPaths.map((path) => (
          <motion.path
            key={path.id}
            d={`M ${path.startX} ${path.startY} Q ${(path.startX + path.endX) / 2} ${Math.min(path.startY, path.endY) - 10} ${path.endX} ${path.endY}`}
            fill="none"
            stroke="url(#flightGradient)"
            strokeWidth="0.2"
            strokeDasharray="2 1"
            initial={{ pathLength: 0, opacity: 0 }}
            animate={{ 
              pathLength: [0, 1, 0],
              opacity: [0, 0.8, 0]
            }}
            transition={{
              duration: path.duration,
              delay: path.delay,
              repeat: Infinity,
              ease: "easeInOut"
            }}
          />
        ))}
      </svg>

      {/* Animated dots representing aircraft */}
      {flightPaths.slice(0, 4).map((path, index) => (
        <motion.div
          key={`dot-${path.id}`}
          className="absolute w-1 h-1 bg-blue-400 rounded-full shadow-lg"
          style={{
            left: `${path.startX}%`,
            top: `${path.startY}%`,
          }}
          animate={{
            x: [`0%`, `${(path.endX - path.startX) * 4}px`],
            y: [`0%`, `${(path.endY - path.startY) * 4}px`],
          }}
          transition={{
            duration: path.duration * 0.8,
            delay: path.delay + 1,
            repeat: Infinity,
            ease: "easeInOut"
          }}
        />
      ))}
    </div>
  )
}
