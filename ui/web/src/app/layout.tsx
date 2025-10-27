import type { Metadata } from 'next'
import Link from 'next/link'
import './globals.css'
import { Toaster } from 'react-hot-toast'
import LLMMessageDisplay from './components/LLMMessageDisplay'

export const metadata: Metadata = {
  title: 'AiAir AeroOps',
  description: 'AiAir Flight Operations Management System',
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
          className="pointer-events-none fixed inset-0 -z-10 bg-cover bg-center bg-no-repeat"
          style={{ backgroundImage: "url(/aeroOps.png)" }}
        />
        <div
          aria-hidden="true"
          className="pointer-events-none fixed inset-0 -z-10 bg-gradient-to-br from-slate-50/90 via-blue-50/60 to-gray-50/70"
        />
        <div className="relative z-10 flex min-h-screen flex-col">
          <header className="sticky top-0 z-30 border-b border-white/20 bg-white/80 backdrop-blur-xl shadow-sm">
            <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8">
              <Link href="/" className="flex items-center space-x-3 group">
                <div className="bg-gradient-to-br from-blue-600 to-gray-600 p-2 rounded-lg shadow-lg group-hover:shadow-xl transition-all duration-300 group-hover:scale-105">
                  <svg className="h-6 w-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                </div>
                <span className="text-lg font-bold bg-gradient-to-r from-gray-900 to-gray-700 bg-clip-text text-transparent">
                  AiAir AeroOps
                </span>
              </Link>
              <nav className="flex flex-wrap items-center gap-1 text-sm font-medium">
                {navLinks.map(link => (
                  <Link
                    key={link.href}
                    href={link.href}
                    className="rounded-lg px-3 py-2 text-slate-700 transition-all duration-200 hover:bg-slate-900/10 hover:text-slate-900 hover:scale-105"
                  >
                    {link.label}
                  </Link>
                ))}
              </nav>
              <Link
                href="mailto:hello@aeroops.ai"
                className="hidden rounded-full border border-cyan-400/40 bg-cyan-500/20 px-4 py-2 text-xs font-semibold uppercase tracking-[0.3em] text-white shadow-lg shadow-cyan-500/20 backdrop-blur md:inline-flex"
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
