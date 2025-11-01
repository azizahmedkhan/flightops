'use client'

import React from 'react'

interface AeroOpsLogoProps {
  size?: number | string
  className?: string
  variant?: 'full' | 'icon' | 'compact'
  animated?: boolean
}

export default function AeroOpsLogo({ 
  size = 48, 
  className = '',
  variant = 'full',
  animated = true
}: AeroOpsLogoProps) {
  const iconSize = typeof size === 'number' ? size : size
  
  if (variant === 'icon') {
    return (
      <svg
        width={iconSize}
        height={iconSize}
        viewBox="0 0 120 120"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className={className}
      >
        <defs>
          <linearGradient id="logoGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#2563EB" stopOpacity="1" />
            <stop offset="50%" stopColor="#475569" stopOpacity="1" />
            <stop offset="100%" stopColor="#1E293B" stopOpacity="1" />
          </linearGradient>
          <linearGradient id="chatGlow" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#3B82F6" stopOpacity="0.4" />
            <stop offset="100%" stopColor="#64748B" stopOpacity="0.2" />
          </linearGradient>
        </defs>
        
        {/* Unified chat box - main element */}
        <rect
          x="20"
          y="25"
          width="80"
          height="70"
          rx="12"
          fill="url(#logoGradient)"
          opacity="0.95"
        />
        
        {/* Inner chat bubble representation - unified operations */}
        <rect
          x="30"
          y="35"
          width="60"
          height="50"
          rx="8"
          fill="white"
          opacity="0.9"
        />
        
        {/* Multiple conversation lines converging into one */}
        <g opacity="0.7">
          {/* Converging lines symbolizing unified operations */}
          <path
            d="M 10 40 Q 15 50 25 45"
            stroke="url(#logoGradient)"
            strokeWidth="3"
            strokeLinecap="round"
            fill="none"
            className={animated ? "animate-pulse" : ""}
          />
          <path
            d="M 10 60 Q 15 50 25 55"
            stroke="url(#logoGradient)"
            strokeWidth="3"
            strokeLinecap="round"
            fill="none"
            className={animated ? "animate-pulse" : ""}
          />
          <path
            d="M 10 80 Q 15 70 25 65"
            stroke="url(#logoGradient)"
            strokeWidth="3"
            strokeLinecap="round"
            fill="none"
            className={animated ? "animate-pulse" : ""}
          />
          
          {/* Outgoing unified response */}
          <path
            d="M 90 50 Q 105 50 110 60"
            stroke="url(#logoGradient)"
            strokeWidth="3"
            strokeLinecap="round"
            fill="none"
            opacity="0.6"
            className={animated ? "animate-pulse" : ""}
          />
        </g>
        
        {/* Small plane icon inside - subtle aviation reference */}
        <g transform="translate(60, 60)">
          <path
            d="M -8 0 L -12 -6 L -8 -3 L 0 0 L -8 3 L -12 6 Z"
            fill="url(#logoGradient)"
            opacity="0.6"
          />
        </g>
        
        {/* Sparkle/Intelligence indicator */}
        <circle
          cx="85"
          cy="35"
          r="4"
          fill="#3B82F6"
          opacity="0.9"
          className={animated ? "animate-pulse" : ""}
        />
        
        {/* Glow effect behind chat box */}
        <rect
          x="15"
          y="20"
          width="90"
          height="80"
          rx="15"
          fill="url(#chatGlow)"
          opacity="0.3"
          className={animated ? "animate-pulse" : ""}
        />
      </svg>
    )
  }

  if (variant === 'compact') {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <svg
          width={iconSize}
          height={iconSize}
          viewBox="0 0 120 120"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <defs>
            <linearGradient id="compactGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#2563EB" />
              <stop offset="50%" stopColor="#475569" />
              <stop offset="100%" stopColor="#1E293B" />
            </linearGradient>
          </defs>
          <rect x="20" y="25" width="80" height="70" rx="12" fill="url(#compactGradient)" />
          <rect x="30" y="35" width="60" height="50" rx="8" fill="white" opacity="0.9" />
          <path d="M -8 0 L -12 -6 L -8 -3 L 0 0 L -8 3 L -12 6 Z" fill="url(#compactGradient)" opacity="0.6" transform="translate(60, 60)" />
        </svg>
        <span className="text-lg font-bold bg-gradient-to-r from-blue-600 via-slate-600 to-gray-700 bg-clip-text text-transparent">
          AeroOps
        </span>
      </div>
    )
  }

  // Full variant
  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <svg
        width={iconSize}
        height={iconSize}
        viewBox="0 0 120 120"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <linearGradient id="fullGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#2563EB" stopOpacity="1" />
            <stop offset="50%" stopColor="#475569" stopOpacity="1" />
            <stop offset="100%" stopColor="#1E293B" stopOpacity="1" />
          </linearGradient>
          <linearGradient id="fullGlow" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#3B82F6" stopOpacity="0.4" />
            <stop offset="100%" stopColor="#64748B" stopOpacity="0.2" />
          </linearGradient>
        </defs>
        
        <rect
          x="15"
          y="20"
          width="90"
          height="80"
          rx="15"
          fill="url(#fullGlow)"
          opacity="0.3"
          className={animated ? "animate-pulse" : ""}
        />
        
        <rect
          x="20"
          y="25"
          width="80"
          height="70"
          rx="12"
          fill="url(#fullGradient)"
          opacity="0.95"
        />
        
        <rect
          x="30"
          y="35"
          width="60"
          height="50"
          rx="8"
          fill="white"
          opacity="0.9"
        />
        
        <g opacity="0.7">
          <path
            d="M 10 40 Q 15 50 25 45"
            stroke="url(#fullGradient)"
            strokeWidth="3"
            strokeLinecap="round"
            fill="none"
            className={animated ? "animate-pulse" : ""}
          />
          <path
            d="M 10 60 Q 15 50 25 55"
            stroke="url(#fullGradient)"
            strokeWidth="3"
            strokeLinecap="round"
            fill="none"
            className={animated ? "animate-pulse" : ""}
          />
          <path
            d="M 10 80 Q 15 70 25 65"
            stroke="url(#fullGradient)"
            strokeWidth="3"
            strokeLinecap="round"
            fill="none"
            className={animated ? "animate-pulse" : ""}
          />
        </g>
        
        <g transform="translate(60, 60)">
          <path
            d="M -8 0 L -12 -6 L -8 -3 L 0 0 L -8 3 L -12 6 Z"
            fill="url(#fullGradient)"
            opacity="0.6"
          />
        </g>
        
        <circle
          cx="85"
          cy="35"
          r="4"
          fill="#3B82F6"
          opacity="0.9"
          className={animated ? "animate-pulse" : ""}
        />
      </svg>
      <div className="flex flex-col">
        <span className="text-xl font-bold bg-gradient-to-r from-blue-600 via-slate-600 to-gray-700 bg-clip-text text-transparent leading-tight">
          AeroOps AI
        </span>
        <span className="text-xs text-gray-600 font-medium">One Chat. All Operations.</span>
      </div>
    </div>
  )
}
