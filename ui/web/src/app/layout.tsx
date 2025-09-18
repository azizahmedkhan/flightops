import type { Metadata } from 'next'
import Link from 'next/link'
import { Inter } from 'next/font/google'
import './globals.css'
import { Toaster } from 'react-hot-toast'
import LLMMessageDisplay from './components/LLMMessageDisplay'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Air New Zealand FlightOps',
  description: 'Air New Zealand Flight Operations Management System',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const navLinks = [
    { href: '/', label: 'Home' },
    { href: '/search', label: 'Search' },
    { href: '/data', label: 'Data Insights' },
    { href: '/monitoring', label: 'Monitoring' },
    { href: '/customer-chat', label: 'Customer Chat' },
    { href: '/comms', label: 'Communications' },
    { href: '/query', label: 'Agent Query' },
    { href: '/llm-audit', label: 'LLM Audit' },
  ]

  return (
    <html lang="en">
      <body className={`${inter.className} relative min-h-screen`}>
        <div
          aria-hidden="true"
          className="pointer-events-none fixed inset-0 -z-10 bg-cover bg-center bg-no-repeat"
          style={{ backgroundImage: "url(/air_nz_plane.png)" }}
        />
        <div
          aria-hidden="true"
          className="pointer-events-none fixed inset-0 -z-10 bg-gradient-to-br from-slate-50/85 via-gray-100/80 to-slate-200/85"
        />
        <div className="relative z-10 flex min-h-screen flex-col">
          <header className="sticky top-0 z-20 border-b border-white/40 bg-white/70 backdrop-blur-sm">
            <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8">
              <Link href="/" className="text-lg font-semibold text-slate-900">
                Air New Zealand FlightOps
              </Link>
              <nav className="flex flex-wrap items-center gap-3 text-sm font-medium text-slate-700">
                {navLinks.map(link => (
                  <Link
                    key={link.href}
                    href={link.href}
                    className="rounded-md px-3 py-1 transition hover:bg-slate-900/10 hover:text-slate-900"
                  >
                    {link.label}
                  </Link>
                ))}
              </nav>
            </div>
          </header>

          <main className="flex-1 px-0 pb-10 pt-6 sm:pt-8">
            {children}
          </main>

          {/* LLM Message Display - Fixed position */}
          <div className="fixed bottom-4 right-4 z-30 w-96 max-w-[calc(100vw-2rem)]">
            <LLMMessageDisplay />
          </div>

          <Toaster position="top-right" />
        </div>
      </body>
    </html>
  )
}
