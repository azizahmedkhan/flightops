import type { Metadata } from 'next'
import Link from 'next/link'
import './globals.css'
import { Toaster } from 'react-hot-toast'
import LLMMessageDisplay from './components/LLMMessageDisplay'

export const metadata: Metadata = {
  title: 'AeroOps Command Center',
  description: 'AeroOps — the intelligent command center for airline operations teams.',
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
    { href: '/chatbot', label: 'Scalable Chat' },
    { href: '/comms', label: 'Communications' },
    { href: '/query', label: 'Agent Query' },
    { href: '/llm-audit', label: 'LLM Audit' },
  ]

  return (
    <html lang="en">
      <body className="relative min-h-screen bg-slate-950 text-slate-100">
        <div className="relative z-10 flex min-h-screen flex-col">
          <header className="sticky top-0 z-30 border-b border-white/10 bg-black/60 backdrop-blur">
            <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8">
              <Link href="/" className="text-lg font-semibold tracking-[0.3em] text-slate-100">
                AEROOPS
              </Link>
              <nav className="flex flex-wrap items-center gap-2 text-xs font-semibold uppercase tracking-[0.25em] text-slate-300">
                {navLinks.map(link => (
                  <Link
                    key={link.href}
                    href={link.href}
                    className="rounded-full border border-white/10 px-3 py-1 transition hover:border-cyan-400/60 hover:text-white"
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
