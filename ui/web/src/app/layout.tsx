import type { Metadata } from 'next'
import Link from 'next/link'
import './globals.css'
import { Toaster } from 'react-hot-toast'
import LLMMessageDisplay from './components/LLMMessageDisplay'
import AeroOpsLogo from './components/AeroOpsLogo'

export const metadata: Metadata = {
  title: 'AiAir AeroOps',
  description: 'AiAir Flight Operations Management System - One Chat. All Operations.',
  icons: {
    icon: [
      { url: '/favicon.svg', type: 'image/svg+xml' },
      { url: '/aeroops-logo-icon.svg', type: 'image/svg+xml', sizes: '48x48' },
    ],
    apple: [
      { url: '/apple-touch-icon.svg', type: 'image/svg+xml', sizes: '180x180' },
    ],
  },
  manifest: '/manifest.json',
  themeColor: '#2563EB',
  viewport: 'width=device-width, initial-scale=1, maximum-scale=5',
  appleWebApp: {
    capable: true,
    statusBarStyle: 'default',
    title: 'AeroOps',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const navLinks = [
    { href: '/', label: 'Home' },
    { href: '/old-landing', label: 'Old Landing' },
    { href: '/search', label: 'Search' },
    { href: '/data', label: 'Data Insights' },
    { href: '/monitoring', label: 'Monitoring' },
    { href: '/customer-chat', label: 'Customer Chat' },
    { href: '/chatbot', label: 'Scalable Chat' },
    { href: '/comms', label: 'Communications' },
    { href: '/query', label: 'Agent Query' },
    { href: '/llm-audit', label: 'LLM Audit' },
  ]

  return (
    <html lang="en">
      <body className="relative min-h-screen">
        <div
          aria-hidden="true"
          className="pointer-events-none fixed inset-0 -z-10 bg-gradient-to-br from-blue-50 via-slate-50 to-gray-50"
        />
        <div
          aria-hidden="true"
          className="pointer-events-none fixed inset-0 -z-10 gradient-liquid-1"
        />
        <div className="relative z-10 flex min-h-screen flex-col">
          <header className="glass-header sticky top-0 z-30">
            <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8">
              <Link href="/" className="flex items-center space-x-3 group">
                <div className="group-hover:scale-105 transition-transform duration-300">
                  <AeroOpsLogo size={40} variant="icon" />
                </div>
                <span className="text-lg font-bold bg-gradient-to-r from-blue-600 via-slate-600 to-gray-700 bg-clip-text text-transparent">
                  AiAir AeroOps
                </span>
              </Link>
              <nav className="flex flex-wrap items-center gap-1 text-sm font-medium">
                {navLinks.map(link => (
                  <Link
                    key={link.href}
                    href={link.href}
                    className="glass-button rounded-xl px-4 py-2 text-gray-700 transition-all duration-200 hover:scale-105"
                  >
                    {link.label}
                  </Link>
                ))}
              </nav>
              <Link
                href="mailto:hello@aeroops.ai"
                className="hidden glass-button rounded-full px-5 py-2 text-xs font-semibold uppercase tracking-[0.3em] text-gray-700 md:inline-flex"
              >
                Connect
              </Link>
            </div>
          </header>

          <main className="flex-1 px-0 pb-10 pt-0">{children}</main>

          <div className="fixed bottom-4 right-4 z-30 w-96 max-w-[calc(100vw-2rem)]">
            <LLMMessageDisplay />
          </div>

          <Toaster position="top-right" />
        </div>
      </body>
    </html>
  )
}
