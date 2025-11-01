import type { CSSProperties } from 'react'
import AeroOpsLogo from '../components/AeroOpsLogo'

type Stat = {
  label: string
  value: string
}

type Feature = {
  icon: string
  title: string
  description: string
  highlight: string
}

type WorkflowStep = {
  time: string
  title: string
  detail: string
}

const stats: Stat[] = [
  { label: 'On-time performance lift', value: '▲ 12%' },
  { label: 'Delay predictions', value: '97% accuracy' },
  { label: 'Operational savings', value: '$4.3M / yr' },
  { label: 'Crew swaps automated', value: '840 / mo' },
]

const features: Feature[] = [
  {
    icon: '🛰️',
    title: 'Live Operations Canvas',
    description:
      'Fuse flight tracking, crew rosters, maintenance schedules, and weather into a living source of truth.',
    highlight: 'Hyper-focused alerts anticipate disruptions hours before they appear on public radars.',
  },
  {
    icon: '🧠',
    title: 'Adaptive AI Copilot',
    description:
      'An orchestration layer that drafts comms, proposes recovery plans, and coordinates stakeholders instantly.',
    highlight: 'Every recommendation cites data lineage so controllers can make confident, auditable decisions.',
  },
  {
    icon: '⚡',
    title: 'Workflow Automations',
    description:
      'Trigger crew notifications, reroute aircraft, and sync systems with no-code playbooks tailored to your airline.',
    highlight: 'AeroOps integrates with your stack, from ACARS to Slack, without compromising safety gates.',
  },
]

const workflow: WorkflowStep[] = [
  {
    time: 'T-6 hrs',
    title: 'Demand surge detected',
    detail: 'AI models sense atypical load factors across the morning bank and spin up proactive recovery options.',
  },
  {
    time: 'T-2 hrs',
    title: 'Weather deviations plotted',
    detail: 'AeroOps simulates 12 routing scenarios, highlighting a reroute that protects crew duty limits.',
  },
  {
    time: 'Gate',
    title: 'Comms launched automatically',
    detail: 'Passengers and crew receive synchronized updates while ops monitors a confidence feed in real time.',
  },
]

const integrations = ['FlightAware', 'SITA', 'Amadeus', 'Snowflake', 'Slack', 'PagerDuty']

const testimonial = {
  quote:
    '"AeroOps transformed our nerve center. We see what matters sooner, act faster, and close the loop with passengers without breaking a sweat."',
  author: 'Leilani Moore',
  role: 'Director of Integrated Operations, Pacific Horizon Air',
}

type GlowOrbProps = {
  className?: string
  color: string
  size?: string
  opacity?: number
}

function GlowOrb({ className = '', color, size = '30rem', opacity = 0.55 }: GlowOrbProps) {
  const style: CSSProperties = {
    background: `radial-gradient(circle, ${color} 0%, transparent 65%)`,
    width: size,
    height: size,
    opacity,
  }

  return <div className={`pointer-events-none absolute rounded-full blur-3xl ${className}`} style={style} />
}

function FlightPath() {
  return (
    <svg viewBox="0 0 360 200" className="h-full w-full">
      <defs>
        <linearGradient id="flight-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#3B82F6" stopOpacity="0.4" />
          <stop offset="100%" stopColor="#475569" stopOpacity="0.9" />
        </linearGradient>
      </defs>
      <path
        d="M20 160 C 120 20, 220 220, 340 80"
        fill="none"
        stroke="url(#flight-gradient)"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeDasharray="12 12"
        className="animate-dash"
      />
      <g className="animate-float" transform="translate(0, -8)">
        <circle cx="340" cy="80" r="8" fill="#3B82F6" />
        <path d="M330 80 L342 83 L338 80 L342 77 Z" fill="#475569" opacity={0.9} />
      </g>
      <g>
        <circle cx="70" cy="120" r="5" fill="#CBD5E1" opacity={0.8} />
        <circle cx="140" cy="70" r="5" fill="#CBD5E1" opacity={0.8} />
        <circle cx="220" cy="140" r="5" fill="#CBD5E1" opacity={0.8} />
      </g>
    </svg>
  )
}

function FeatureCard({ feature }: { feature: Feature }) {
  return (
    <article className="group relative overflow-hidden rounded-3xl border border-white/30 bg-white/70 p-8 backdrop-blur-2xl transition-transform duration-300 hover:-translate-y-2 hover:border-blue-300/50 glass-card">
      <div className="absolute -right-16 -top-16 h-40 w-40 rounded-full bg-blue-500/10 blur-3xl transition-opacity duration-300 group-hover:opacity-100" />
      <div className="relative">
        <span className="text-3xl">{feature.icon}</span>
        <h3 className="mt-4 text-2xl font-semibold text-gray-900">{feature.title}</h3>
        <p className="mt-3 text-base leading-relaxed text-gray-700">{feature.description}</p>
        <p className="mt-4 rounded-2xl border border-blue-300/30 bg-blue-50/50 p-4 text-sm text-gray-700">
          {feature.highlight}
        </p>
      </div>
    </article>
  )
}

function WorkflowItem({ step }: { step: WorkflowStep }) {
  return (
    <div className="relative pl-10">
      <div className="absolute left-0 top-1 h-3 w-3 rounded-full border border-blue-400 bg-blue-500" />
      <div className="absolute left-1 top-1 h-full w-px bg-gradient-to-b from-blue-400/40 via-blue-400/10 to-transparent" />
      <div className="rounded-3xl border border-white/30 bg-white/70 p-6 backdrop-blur-2xl glass-card">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-blue-600">{step.time}</p>
        <h4 className="mt-2 text-xl font-semibold text-gray-900">{step.title}</h4>
        <p className="mt-3 text-sm leading-relaxed text-gray-700">{step.detail}</p>
      </div>
    </div>
  )
}

export default function HomePage() {
  const year = new Date().getFullYear()

  return (
    <div className="relative min-h-screen overflow-hidden">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute inset-0 bg-gradient-to-br from-blue-50 via-slate-50 to-gray-50" />
        <div className="absolute inset-0 bg-grid opacity-20" />
        <GlowOrb className="-top-40 -left-20" color="rgba(59, 130, 246, 0.15)" size="36rem" />
        <GlowOrb className="top-1/3 -right-10" color="rgba(100, 116, 139, 0.12)" size="28rem" opacity={0.4} />
        <GlowOrb className="bottom-[-8rem] left-1/2 -translate-x-1/2" color="rgba(71, 85, 105, 0.15)" size="42rem" opacity={0.35} />
      </div>

      <div className="relative z-10">
        <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-8 lg:px-10">
          <div className="flex items-center gap-3">
            <AeroOpsLogo size={48} variant="icon" />
            <div>
              <p className="text-sm font-medium uppercase tracking-[0.3em] text-gray-700">AeroOps</p>
              <p className="text-xs text-gray-600">AI command center for airline operations</p>
            </div>
          </div>
          <div className="hidden items-center gap-6 text-sm text-gray-700 md:flex">
            <a href="#features" className="hover:text-blue-600 transition-colors">Platform</a>
            <a href="#workflow" className="hover:text-blue-600 transition-colors">Playbooks</a>
            <a href="#testimonial" className="hover:text-blue-600 transition-colors">Customer proof</a>
          </div>
          <button className="glass-button hidden rounded-full px-5 py-2 text-sm font-medium text-gray-800 md:inline-flex hover:scale-105 transition-transform">
            Book a live demo
          </button>
        </header>

        <main>
          <section className="mx-auto flex max-w-6xl flex-col gap-16 px-6 pb-24 pt-12 lg:flex-row lg:items-center lg:px-10">
            <div className="flex-1">
              <span className="inline-flex items-center gap-2 rounded-full border border-blue-300/30 bg-blue-50/50 px-4 py-2 text-xs font-semibold uppercase tracking-[0.35em] text-blue-600 glass-card">
                Next-gen airline ops
                <span className="h-2 w-2 rounded-full bg-blue-500 shadow-[0_0_0_6px_rgba(59,130,246,0.25)]" />
              </span>
              <h1 className="mt-6 text-4xl font-semibold leading-tight bg-gradient-to-r from-blue-600 via-slate-600 to-gray-700 bg-clip-text text-transparent md:text-6xl">
                Orchestrate every flight with{' '}
                <span className="text-blue-600">AeroOps</span>
              </h1>
              <p className="mt-6 max-w-xl text-lg leading-relaxed text-gray-700">
                A mission control for network operations teams. AeroOps predicts disruptions, spins up recovery strategies, and keeps crews and passengers in sync—automatically.
              </p>
              <div className="mt-10 flex flex-wrap items-center gap-4">
                <button className="rounded-full bg-gradient-to-r from-blue-600 via-slate-700 to-gray-700 px-6 py-3 text-sm font-semibold text-white shadow-xl shadow-blue-500/30 transition hover:brightness-110 hover:scale-105 glass-button">
                  Launch my command center
                </button>
                <button className="glass-card rounded-full border border-gray-300/50 px-6 py-3 text-sm font-semibold text-gray-800 backdrop-blur transition hover:border-blue-400/50 hover:scale-105">
                  Explore the platform
                </button>
              </div>
              <dl className="mt-14 grid grid-cols-2 gap-6 sm:grid-cols-4">
                {stats.map((stat) => (
                  <div key={stat.label} className="glass-card rounded-3xl border border-white/30 p-5 text-center backdrop-blur hover-glass">
                    <dt className="text-xs font-semibold uppercase tracking-[0.3em] text-gray-600">{stat.label}</dt>
                    <dd className="mt-3 text-xl font-semibold bg-gradient-to-r from-blue-600 to-slate-700 bg-clip-text text-transparent">{stat.value}</dd>
                  </div>
                ))}
              </dl>
            </div>

            <div className="relative flex flex-1 flex-col gap-6">
              <div className="absolute -top-10 left-1/2 h-72 w-72 -translate-x-1/2 rounded-full border border-blue-300/20 bg-blue-400/10 blur-3xl liquid-blob" />
              <div className="glass-liquid relative overflow-hidden rounded-[2.5rem] border border-white/30 p-8 shadow-2xl">
                <div className="flex items-center justify-between text-xs text-gray-600">
                  <span className="uppercase tracking-[0.4em] text-blue-600">Ops Pulse</span>
                  <span className="flex items-center gap-2">
                    <span className="h-2 w-2 animate-pulse rounded-full bg-green-500" />
                    Live feed
                  </span>
                </div>
                <div className="relative mt-6 h-56 overflow-hidden rounded-2xl border border-white/30 bg-gray-100/30 p-4 glass-card">
                  <FlightPath />
                  <div className="absolute inset-x-4 bottom-4 flex items-center justify-between rounded-2xl border border-white/30 bg-white/70 px-4 py-3 text-xs text-gray-700 backdrop-blur glass-card">
                    <div>
                      <p className="font-semibold text-gray-900">AKL ➜ LAX</p>
                      <p className="mt-1 text-[11px] uppercase tracking-[0.35em] text-blue-600">Projected arrival 21m early</p>
                    </div>
                    <div className="text-right">
                      <p className="font-semibold text-gray-900">Crew green</p>
                      <p className="mt-1 text-[11px] uppercase tracking-[0.35em] text-green-600">Turn readiness 96%</p>
                    </div>
                  </div>
                </div>
                <div className="mt-6 grid grid-cols-2 gap-4 text-xs text-gray-700">
                  <div className="glass-card rounded-2xl border border-white/30 p-4">
                    <p className="text-[11px] uppercase tracking-[0.35em] text-blue-600">AI Advisory</p>
                    <p className="mt-2 text-sm text-gray-900">Reassign 2 crew to NZ78 to protect duty limits.</p>
                  </div>
                  <div className="relative glass-card rounded-2xl border border-white/30 p-4">
                    <p className="text-[11px] uppercase tracking-[0.35em] text-blue-600">Passenger sentiment</p>
                    <p className="mt-2 text-sm text-gray-900">92% of guests already notified via preferred channel.</p>
                    <span className="absolute -right-2 -top-2 inline-flex h-10 w-10 items-center justify-center rounded-full bg-blue-400/20 text-base font-semibold text-blue-700 shadow-lg">
                      +17%
                    </span>
                  </div>
                </div>
              </div>
              <div className="glass-card flex items-center justify-between rounded-3xl border border-white/30 p-5 text-xs text-gray-700 backdrop-blur">
                <div>
                  <p className="uppercase tracking-[0.4em] text-blue-600">System Health</p>
                  <p className="mt-2 text-sm text-gray-900">Data pipelines nominal · Models synced 4 minutes ago</p>
                </div>
                <div className="relative flex h-14 w-14 items-center justify-center rounded-full border border-blue-400/20 bg-blue-500/10">
                  <div className="absolute inset-0 rounded-full border border-blue-300/40" />
                  <div className="absolute inset-1 rounded-full border border-blue-200/40" />
                  <span className="relative text-lg font-semibold text-blue-700">99</span>
                </div>
              </div>
            </div>
          </section>

          <section id="features" className="py-24">
            <div className="mx-auto max-w-6xl px-6 lg:px-10">
              <div className="mx-auto max-w-3xl text-center">
                <p className="text-xs font-semibold uppercase tracking-[0.4em] text-blue-600">Platform capabilities</p>
                <h2 className="mt-4 text-3xl font-semibold bg-gradient-to-r from-blue-600 via-slate-600 to-gray-700 bg-clip-text text-transparent md:text-4xl">
                  Everything your ops center needs in one adaptive surface
                </h2>
                <p className="mt-4 text-base leading-relaxed text-gray-700">
                  Designed with controllers, dispatchers, and customer teams to orchestrate complex networks with calm precision.
                </p>
              </div>
              <div className="mt-16 grid gap-8 md:grid-cols-3">
                {features.map((feature) => (
                  <FeatureCard key={feature.title} feature={feature} />
                ))}
              </div>
            </div>
          </section>

          <section id="workflow" className="py-24">
            <div className="mx-auto max-w-6xl px-6 lg:px-10">
              <div className="grid gap-16 lg:grid-cols-[1fr_1.2fr] lg:items-center">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.4em] text-blue-600">Playbook in action</p>
                  <h2 className="mt-4 text-3xl font-semibold bg-gradient-to-r from-blue-600 via-slate-600 to-gray-700 bg-clip-text text-transparent md:text-4xl">
                    See how AeroOps guides teams through disruption
                  </h2>
                  <p className="mt-4 text-base leading-relaxed text-gray-700">
                    The platform senses irregular ops, proposes confident resolutions, and keeps every stakeholder aligned—without burning out your controllers.
                  </p>
                </div>
                <div className="space-y-8">
                  {workflow.map((step) => (
                    <WorkflowItem key={step.title} step={step} />
                  ))}
                </div>
              </div>
            </div>
          </section>

          <section className="py-24" id="testimonial">
            <div className="mx-auto max-w-5xl px-6 text-center lg:px-10">
              <div className="glass-liquid relative overflow-hidden rounded-[2.75rem] border border-white/30 p-10 shadow-2xl">
                <div className="absolute -left-24 -top-24 h-72 w-72 rounded-full bg-blue-500/10 blur-3xl liquid-blob" />
                <div className="absolute -bottom-24 right-10 h-56 w-56 rounded-full bg-slate-500/10 blur-3xl liquid-blob" />
                <div className="relative">
                  <p className="text-lg leading-relaxed text-gray-800 md:text-xl">{testimonial.quote}</p>
                  <div className="mt-8 flex flex-col items-center gap-1 text-sm text-gray-700">
                    <span className="font-semibold text-gray-900">{testimonial.author}</span>
                    <span>{testimonial.role}</span>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section className="py-20">
            <div className="mx-auto max-w-5xl px-6 text-center lg:px-10">
              <p className="text-xs font-semibold uppercase tracking-[0.4em] text-blue-600">Trusted connections</p>
              <div className="mt-8 grid grid-cols-2 gap-6 text-sm text-gray-700 sm:grid-cols-3 md:text-base">
                {integrations.map((logo) => (
                  <div key={logo} className="glass-card rounded-2xl border border-white/30 px-6 py-4 text-center backdrop-blur hover-glass">
                    {logo}
                  </div>
                ))}
              </div>
            </div>
          </section>

          <section className="pb-24">
            <div className="mx-auto max-w-5xl overflow-hidden rounded-[2.5rem] border border-blue-400/30 bg-white/70 px-10 py-16 text-center shadow-2xl glass-liquid">
              <p className="text-xs font-semibold uppercase tracking-[0.4em] text-blue-600">Ready for wheels up</p>
              <h2 className="mt-4 text-3xl font-semibold bg-gradient-to-r from-blue-600 via-slate-600 to-gray-700 bg-clip-text text-transparent md:text-4xl">
                Bring calm to the chaos of airline operations
              </h2>
              <p className="mt-4 text-base leading-relaxed text-gray-700">
                Let AeroOps become your always-on co-strategist—from planning to day-of-execution, across every airport, aircraft, and crew.
              </p>
              <div className="mt-8 flex flex-wrap justify-center gap-4">
                <button className="rounded-full bg-gradient-to-r from-blue-600 via-slate-700 to-gray-700 px-7 py-3 text-sm font-semibold text-white shadow-xl shadow-blue-500/40 transition hover:brightness-110 hover:scale-105 glass-button">
                  Schedule a strategy session
                </button>
                <button className="glass-card rounded-full border border-gray-300/50 px-7 py-3 text-sm font-semibold text-gray-800 backdrop-blur transition hover:border-blue-400/50 hover:scale-105">
                  Download the product brief
                </button>
              </div>
            </div>
          </section>
        </main>

        <footer className="border-t border-white/30 bg-white/40 backdrop-blur py-10">
          <div className="mx-auto flex max-w-6xl flex-col gap-4 px-6 text-xs text-gray-600 sm:flex-row sm:items-center sm:justify-between lg:px-10">
            <p>© {year} AeroOps. Engineered for resilient airline operations.</p>
            <div className="flex gap-6">
              <a href="#features" className="hover:text-blue-600 transition-colors">Platform</a>
              <a href="#workflow" className="hover:text-blue-600 transition-colors">Playbooks</a>
              <a href="#testimonial" className="hover:text-blue-600 transition-colors">Stories</a>
            </div>
          </div>
        </footer>
      </div>
    </div>
  )
}
