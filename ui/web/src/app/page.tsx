'use client'

import Link from 'next/link'
import { motion, useScroll, useTransform, useInView } from 'framer-motion'
import { useInView as useInViewObserver } from 'react-intersection-observer'
import { useRef, useEffect, useState } from 'react'
import { 
  Plane, 
  MessageSquare, 
  Search, 
  Database, 
  Activity,
  ArrowRight,
  Zap,
  Users,
  Bot,
  Globe,
  Shield,
  Clock,
  TrendingUp,
  Star,
  CheckCircle
} from 'lucide-react'
import LLMTestComponent from './components/LLMTestComponent'
import AnimatedFlightPaths from './components/AnimatedFlightPaths'

// Animated Counter Component
function AnimatedCounter({ value, duration = 2000 }: { value: number; duration?: number }) {
  const [count, setCount] = useState(0)
  const { ref, inView } = useInViewObserver({
    threshold: 0.3,
    triggerOnce: true
  })

  useEffect(() => {
    if (inView) {
      let startTime: number
      const animate = (currentTime: number) => {
        if (!startTime) startTime = currentTime
        const progress = Math.min((currentTime - startTime) / duration, 1)
        setCount(Math.floor(progress * value))
        
        if (progress < 1) {
          requestAnimationFrame(animate)
        }
      }
      requestAnimationFrame(animate)
    }
  }, [inView, value, duration])

  return <span ref={ref}>{count.toLocaleString()}</span>
}

// Floating Plane Animation Component
function FloatingPlane({ className, delay = 0 }: { className?: string; delay?: number }) {
  return (
    <motion.div
      className={className}
      animate={{
        y: [-10, 10, -10],
        x: [-5, 5, -5],
        rotate: [-2, 2, -2]
      }}
      transition={{
        duration: 6,
        delay,
        repeat: Infinity,
        ease: "easeInOut"
      }}
    >
      <Plane className="h-8 w-8 text-gray-700/70" />
    </motion.div>
  )
}

export default function HomePage() {
  const { scrollYProgress } = useScroll()
  const heroRef = useRef(null)
  const featuresRef = useRef(null)
  const statsRef = useRef(null)
  
  const y1 = useTransform(scrollYProgress, [0, 1], [0, -150])
  const y2 = useTransform(scrollYProgress, [0, 1], [0, -300])
  const opacity = useTransform(scrollYProgress, [0, 0.3], [1, 0])

  const features = [
    {
      title: 'Flight Query',
      description: 'Ask questions about flight disruptions and get AI-powered insights',
      icon: Plane,
      href: '/query',
      gradient: 'from-blue-600 to-gray-600'
    },
    {
      title: 'Predictive Analytics',
      description: 'AI-powered disruption prediction and proactive management',
      icon: Zap,
      href: '/predictive',
      gradient: 'from-yellow-500 to-orange-600'
    },
    {
      title: 'Crew Management',
      description: 'Intelligent crew optimization and resource management',
      icon: Users,
      href: '/crew',
      gradient: 'from-green-500 to-teal-600'
    },
    {
      title: 'Draft Communications',
      description: 'Generate empathetic customer communications with policy grounding',
      icon: MessageSquare,
      href: '/comms',
      gradient: 'from-slate-600 to-blue-600'
    },
    {
      title: 'Knowledge Search',
      description: 'Search through policies and procedures with semantic search',
      icon: Search,
      href: '/search',
      gradient: 'from-indigo-600 to-blue-600'
    },
    {
      title: 'Data Management',
      description: 'Manage flight data, bookings, and crew rosters',
      icon: Database,
      href: '/data',
      gradient: 'from-gray-700 to-gray-900'
    },
    {
      title: 'System Monitoring',
      description: 'Monitor service health and performance metrics',
      icon: Activity,
      href: '/monitoring',
      gradient: 'from-red-500 to-orange-600'
    },
    {
      title: 'Customer Communication',
      description: 'Test customer chat, email, and SMS communication',
      icon: MessageSquare,
      href: '/customer-chat',
      gradient: 'from-cyan-500 to-blue-600'
    },
    {
      title: 'Scalable Chatbot',
      description: 'High-performance chatbot supporting 1000+ concurrent sessions',
      icon: Bot,
      href: '/chatbot',
      gradient: 'from-gray-600 to-gray-700'
    }
  ]

  const stats = [
    { label: 'Flights Monitored Daily', value: 2500, icon: Plane },
    { label: 'AI Predictions Made', value: 15000, icon: TrendingUp },
    { label: 'Customer Interactions', value: 45000, icon: MessageSquare },
    { label: 'System Uptime', value: 99.9, suffix: '%', icon: Shield }
  ]

  const benefits = [
    'Real-time flight disruption management',
    'Automated customer communication',
    'Predictive maintenance scheduling',
    'Intelligent crew optimization',
    'Policy-grounded AI responses',
    '24/7 system monitoring'
  ]

  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* Liquid Blob Background Elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {/* Animated Flight Paths */}
        <AnimatedFlightPaths />
        
        {/* Floating Liquid Blobs */}
        <motion.div
          style={{ y: y1 }}
          className="absolute -top-24 -left-24 w-96 h-96 bg-gradient-to-br from-blue-400/20 to-slate-400/20 liquid-blob blur-3xl"
        />
        <motion.div
          style={{ y: y2, animationDelay: '2s' } as any}
          className="absolute -bottom-24 -right-24 w-96 h-96 bg-gradient-to-br from-slate-400/20 to-gray-400/20 liquid-blob blur-3xl"
        />
        <motion.div
          style={{ animationDelay: '4s' } as any}
          className="absolute top-1/3 left-1/2 w-80 h-80 bg-gradient-to-br from-slate-300/15 to-blue-300/15 liquid-blob blur-3xl"
        />
        
        {/* Floating Planes */}
        <FloatingPlane className="absolute top-20 left-1/4" delay={0} />
        <FloatingPlane className="absolute top-40 right-1/3" delay={1} />
        <FloatingPlane className="absolute bottom-40 left-1/3" delay={2} />
      </div>

      {/* Hero Section */}
      <motion.section
        ref={heroRef}
        style={{ opacity }}
        className="relative min-h-screen flex items-center justify-center px-4 sm:px-6 lg:px-8"
      >
        <div className="text-center max-w-6xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="mb-8"
          >
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: 0.2, duration: 0.6, type: "spring" }}
              className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-blue-600 via-slate-700 to-gray-700 rounded-3xl mb-8 shadow-2xl"
            >
              <Zap className="h-10 w-10 text-white" />
            </motion.div>
            
            <motion.h1
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4, duration: 0.8 }}
              className="text-6xl md:text-7xl font-bold bg-gradient-to-r from-blue-600 via-slate-600 to-gray-700 bg-clip-text text-transparent mb-6"
            >
              AeroOps AI
            </motion.h1>
          </motion.div>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6, duration: 0.8 }}
            className="text-xl md:text-2xl text-gray-700 max-w-4xl mx-auto mb-12 leading-relaxed font-medium"
          >
            Revolutionizing flight operations with intelligent AI agents that handle disruptions, 
            draft customer communications, and maintain operational excellence with unprecedented precision.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.8, duration: 0.8 }}
            className="flex flex-col sm:flex-row gap-4 justify-center mb-16"
          >
            <Link
              href="/query"
              className="group glass-button px-8 py-4 text-gray-800 font-semibold rounded-full transition-all duration-300 transform hover:scale-105 hover:text-gray-900"
            >
              <span className="flex items-center justify-center">
                <Plane className="mr-2 h-5 w-5" />
                Start Flight Query
                <ArrowRight className="ml-2 h-5 w-5 group-hover:translate-x-1 transition-transform" />
              </span>
            </Link>
            <Link
              href="/chatbot"
              className="glass-card px-8 py-4 text-gray-800 font-semibold rounded-full hover:scale-105 transition-all duration-300"
            >
              Talk to AeroOps
            </Link>
          </motion.div>

          {/* Quick Benefits */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 1, duration: 0.8 }}
            className="grid grid-cols-2 md:grid-cols-3 gap-4 max-w-3xl mx-auto"
          >
            {benefits.slice(0, 3).map((benefit, index) => (
              <motion.div
                key={benefit}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 1.2 + index * 0.1, duration: 0.5 }}
                className="flex items-center text-sm text-gray-600 font-medium"
              >
                <CheckCircle className="h-4 w-4 text-green-500 mr-2 flex-shrink-0" />
                {benefit}
              </motion.div>
            ))}
          </motion.div>
        </div>
      </motion.section>

      {/* Stats Section */}
      <motion.section
        ref={statsRef}
        className="py-20 px-4 sm:px-6 lg:px-8 relative"
      >
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl font-bold bg-gradient-to-r from-blue-600 via-slate-600 to-gray-700 bg-clip-text text-transparent mb-4">
              Powered by Real Performance
            </h2>
            <p className="text-xl text-gray-600">
              See the impact of our AI-powered flight operations system
            </p>
          </motion.div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {stats.map((stat, index) => {
              const Icon = stat.icon
              return (
                <motion.div
                  key={stat.label}
                  initial={{ opacity: 0, y: 30 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1, duration: 0.6 }}
                  viewport={{ once: true }}
                  className="text-center group"
                >
                  <motion.div
                    whileHover={{ scale: 1.1 }}
                    className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-blue-600 via-slate-700 to-gray-700 rounded-full mb-4 shadow-lg group-hover:shadow-2xl transition-all duration-300"
                  >
                    <Icon className="h-8 w-8 text-white" />
                  </motion.div>
                  <div className="text-3xl font-bold bg-gradient-to-r from-blue-600 via-slate-600 to-gray-700 bg-clip-text text-transparent mb-2">
                    <AnimatedCounter value={stat.value} />
                    {stat.suffix && <span>{stat.suffix}</span>}
                  </div>
                  <div className="text-sm text-gray-600 font-medium">
                    {stat.label}
                  </div>
                </motion.div>
              )
            })}
          </div>
        </div>
      </motion.section>

      {/* Features Section */}
      <motion.section
        ref={featuresRef}
        className="py-20 px-4 sm:px-6 lg:px-8 relative"
      >
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl font-bold bg-gradient-to-r from-blue-600 via-slate-600 to-gray-700 bg-clip-text text-transparent mb-4">
              Comprehensive AI Solutions
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              From predictive analytics to customer communications, our platform covers every aspect of modern flight operations.
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map((feature, index) => {
              const Icon = feature.icon
              return (
                <motion.div
                  key={feature.title}
                  initial={{ opacity: 0, y: 30 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1, duration: 0.6 }}
                  viewport={{ once: true }}
                  whileHover={{ y: -5 }}
                  className="group"
                >
                  <Link href={feature.href}>
                    <div className="h-full glass-card hover-glass rounded-3xl p-8 relative overflow-hidden">
                      {/* Gradient Background on Hover */}
                      <div className={`absolute inset-0 bg-gradient-to-br ${feature.gradient} opacity-0 group-hover:opacity-10 transition-opacity duration-300`} />
                      
                      <div className="relative z-10">
                        <motion.div
                          whileHover={{ scale: 1.1, rotate: 5 }}
                          transition={{ type: "spring", stiffness: 300 }}
                          className={`inline-flex items-center justify-center w-14 h-14 bg-gradient-to-br ${feature.gradient} rounded-2xl mb-6 shadow-lg`}
                        >
                          <Icon className="h-7 w-7 text-white" />
                        </motion.div>

                        <h3 className="text-xl font-bold text-gray-900 mb-3 group-hover:text-gray-700 transition-colors">
                          {feature.title}
                        </h3>
                        <p className="text-gray-600 mb-6 leading-relaxed">
                          {feature.description}
                        </p>
                        
                        <div className="flex items-center text-blue-600 font-semibold group-hover:text-slate-600 transition-colors">
                          Explore
                          <ArrowRight className="ml-2 h-4 w-4 group-hover:translate-x-2 transition-transform duration-300" />
                        </div>
                      </div>
                    </div>
                  </Link>
                </motion.div>
              )
            })}
          </div>
        </div>
      </motion.section>

      {/* CTA Section */}
      <motion.section
        initial={{ opacity: 0, y: 30 }}
        whileInView={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8 }}
        viewport={{ once: true }}
        className="py-20 px-4 sm:px-6 lg:px-8 relative"
      >
        <div className="max-w-4xl mx-auto text-center">
          <motion.div
            className="glass-liquid rounded-3xl p-12 relative overflow-hidden"
            whileHover={{ scale: 1.02 }}
            transition={{ type: "spring", stiffness: 300 }}
          >
            {/* Animated background elements */}
            <div className="absolute inset-0 overflow-hidden">
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
                className="absolute -top-10 -right-10 w-32 h-32 border border-blue-300/20 rounded-full liquid-blob"
              />
              <motion.div
                animate={{ rotate: -360 }}
                transition={{ duration: 30, repeat: Infinity, ease: "linear" }}
                className="absolute -bottom-10 -left-10 w-40 h-40 border border-slate-300/10 rounded-full liquid-blob"
              />
            </div>

            <div className="relative z-10">
              <h2 className="text-4xl font-bold bg-gradient-to-r from-blue-600 via-slate-600 to-gray-700 bg-clip-text text-transparent mb-6">
                Ready to Transform Your Operations?
              </h2>
              <p className="text-xl text-gray-600 mb-8 leading-relaxed">
                Join the future of flight operations with AI-powered intelligence that never sleeps.
              </p>
              
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Link
                  href="/query"
                  className="px-8 py-4 glass-button text-gray-800 font-semibold rounded-full transition-all duration-300 transform hover:scale-105"
                >
                  Start Your First Query
                </Link>
                <Link
                  href="/data"
                  className="px-8 py-4 glass-card text-gray-800 font-semibold rounded-full hover:scale-105 transition-all duration-300"
                >
                  Explore Demo Data
                </Link>
              </div>
            </div>
          </motion.div>
        </div>
      </motion.section>

      {/* LLM Test Component */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        viewport={{ once: true }}
        className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-20"
      >
        <LLMTestComponent />
      </motion.div>
    </div>
  )
}
