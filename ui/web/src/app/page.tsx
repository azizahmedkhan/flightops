import type { CSSProperties } from 'react'

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
    '“AeroOps transformed our nerve center. We see what matters sooner, act faster, and close the loop with passengers without breaking a sweat.”',
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
          <stop offset="0%" stopColor="#67e8f9" stopOpacity="0.4" />
          <stop offset="100%" stopColor="#38bdf8" stopOpacity="0.9" />
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
        <circle cx="340" cy="80" r="8" fill="#22d3ee" />
        <path d="M330 80 L342 83 L338 80 L342 77 Z" fill="#0ea5e9" opacity={0.9} />
      </g>
      <g>
        <circle cx="70" cy="120" r="5" fill="#bae6fd" opacity={0.8} />
        <circle cx="140" cy="70" r="5" fill="#bae6fd" opacity={0.8} />
        <circle cx="220" cy="140" r="5" fill="#bae6fd" opacity={0.8} />
      </g>
    </svg>
  )
}

function FeatureCard({ feature }: { feature: Feature }) {
  return (
    <article className="group relative overflow-hidden rounded-3xl border border-white/10 bg-white/5 p-8 backdrop-blur transition-transform duration-300 hover:-translate-y-2 hover:border-cyan-400/40">
      <div className="absolute -right-16 -top-16 h-40 w-40 rounded-full bg-cyan-500/10 blur-3xl transition-opacity duration-300 group-hover:opacity-100" />
      <div className="relative">
        <span className="text-3xl">{feature.icon}</span>
        <h3 className="mt-4 text-2xl font-semibold text-white">{feature.title}</h3>
        <p className="mt-3 text-base leading-relaxed text-slate-300">{feature.description}</p>
        <p className="mt-4 rounded-2xl border border-cyan-400/30 bg-cyan-500/10 p-4 text-sm text-cyan-100">
          {feature.highlight}
        </p>
      </div>
    </article>
  )
}

function WorkflowItem({ step }: { step: WorkflowStep }) {
  return (
    <div className="relative pl-10">
      <div className="absolute left-0 top-1 h-3 w-3 rounded-full border border-cyan-300/80 bg-cyan-400/60" />
      <div className="absolute left-1 top-1 h-full w-px bg-gradient-to-b from-cyan-400/40 via-cyan-400/10 to-transparent" />
      <div className="rounded-3xl border border-white/10 bg-white/5 p-6 backdrop-blur">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-cyan-200/80">{step.time}</p>
        <h4 className="mt-2 text-xl font-semibold text-white">{step.title}</h4>
        <p className="mt-3 text-sm leading-relaxed text-slate-300">{step.detail}</p>
      </div>
    </div>
  )
}

export default function HomePage() {
  const year = new Date().getFullYear()

  return (
    <div className="relative min-h-screen overflow-hidden">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute inset-0 bg-gradient-to-br from-slate-900 via-slate-950 to-black" />
        <div className="absolute inset-0 bg-grid opacity-30" />
        <GlowOrb className="-top-40 -left-20" color="rgba(56, 189, 248, 0.55)" size="36rem" />
        <GlowOrb className="top-1/3 -right-10" color="rgba(14, 165, 233, 0.5)" size="28rem" opacity={0.4} />
        <GlowOrb className="bottom-[-8rem] left-1/2 -translate-x-1/2" color="rgba(59, 130, 246, 0.45)" size="42rem" opacity={0.35} />
      </div>

      <div className="relative z-10">
        <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-8 lg:px-10">
          <div className="flex items-center gap-3">
            <div className="relative flex h-12 w-12 items-center justify-center overflow-hidden rounded-2xl bg-white/10 shadow-lg shadow-cyan-500/20">
              <div className="absolute inset-0 animate-shimmer bg-[linear-gradient(120deg,transparent,rgba(56,189,248,0.45),transparent)]" />
              <span className="relative text-lg font-semibold text-sky-200">AO</span>
            </div>
            <div>
              <p className="text-sm font-medium uppercase tracking-[0.3em] text-slate-300">AeroOps</p>
              <p className="text-xs text-slate-400">AI command center for airline operations</p>
            </div>
          </div>
          <div className="hidden items-center gap-6 text-sm text-slate-300 md:flex">
            <a href="#features">Platform</a>
            <a href="#workflow">Playbooks</a>
            <a href="#testimonial">Customer proof</a>
          </div>
          <button className="hidden rounded-full border border-cyan-400/40 bg-cyan-500/20 px-5 py-2 text-sm font-medium text-white shadow-lg shadow-cyan-500/20 backdrop-blur md:inline-flex">
            Book a live demo
          </button>
        </header>

        <main>
          <section className="mx-auto flex max-w-6xl flex-col gap-16 px-6 pb-24 pt-12 lg:flex-row lg:items-center lg:px-10">
            <div className="flex-1">
              <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-xs font-semibold uppercase tracking-[0.35em] text-cyan-200/90">
                Next-gen airline ops
                <span className="h-2 w-2 rounded-full bg-cyan-300 shadow-[0_0_0_6px_rgba(34,211,238,0.25)]" />
              </span>
              <h1 className="mt-6 text-4xl font-semibold leading-tight text-white md:text-6xl">
                Orchestrate every flight with{' '}
                <span className="bg-gradient-to-r from-sky-300 via-cyan-200 to-blue-400 bg-clip-text text-transparent">AeroOps</span>
              </h1>
              <p className="mt-6 max-w-xl text-lg leading-relaxed text-slate-300">
                A mission control for network operations teams. AeroOps predicts disruptions, spins up recovery strategies, and keeps crews and passengers in sync—automatically.
              </p>
              <div className="mt-10 flex flex-wrap items-center gap-4">
                <button className="rounded-full bg-gradient-to-r from-cyan-400 via-sky-500 to-blue-500 px-6 py-3 text-sm font-semibold text-slate-950 shadow-xl shadow-cyan-500/30 transition hover:brightness-110">
                  Launch my command center
                </button>
                <button className="rounded-full border border-white/20 px-6 py-3 text-sm font-semibold text-white/90 backdrop-blur transition hover:border-white/40">
                  Explore the platform
                </button>
              </div>
              <dl className="mt-14 grid grid-cols-2 gap-6 sm:grid-cols-4">
                {stats.map((stat) => (
                  <div key={stat.label} className="rounded-3xl border border-white/10 bg-white/5 p-5 text-center backdrop-blur">
                    <dt className="text-xs font-semibold uppercase tracking-[0.3em] text-slate-400">{stat.label}</dt>
                    <dd className="mt-3 text-xl font-semibold text-white">{stat.value}</dd>
                  </div>
                ))}
              </dl>
            </div>

            <div className="relative flex flex-1 flex-col gap-6">
              <div className="absolute -top-10 left-1/2 h-72 w-72 -translate-x-1/2 rounded-full border border-cyan-300/20 bg-cyan-400/10 blur-3xl" />
              <div className="relative overflow-hidden rounded-[2.5rem] border border-white/10 bg-white/5 p-8 shadow-2xl shadow-cyan-500/20 backdrop-blur">
                <div className="flex items-center justify-between text-xs text-slate-400">
                  <span className="uppercase tracking-[0.4em] text-cyan-200/80">Ops Pulse</span>
                  <span className="flex items-center gap-2">
                    <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-400" />
                    Live feed
                  </span>
                </div>
                <div className="relative mt-6 h-56 overflow-hidden rounded-2xl border border-white/10 bg-slate-950/60 p-4">
                  <FlightPath />
                  <div className="absolute inset-x-4 bottom-4 flex items-center justify-between rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-xs text-slate-300 backdrop-blur">
                    <div>
                      <p className="font-semibold text-white">AKL ➜ LAX</p>
                      <p className="mt-1 text-[11px] uppercase tracking-[0.35em] text-cyan-200/70">Projected arrival 21m early</p>
                    </div>
                    <div className="text-right">
                      <p className="font-semibold text-white">Crew green</p>
                      <p className="mt-1 text-[11px] uppercase tracking-[0.35em] text-emerald-200/70">Turn readiness 96%</p>
                    </div>
                  </div>
                </div>
                <div className="mt-6 grid grid-cols-2 gap-4 text-xs text-slate-300">
                  <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                    <p className="text-[11px] uppercase tracking-[0.35em] text-cyan-200/70">AI Advisory</p>
                    <p className="mt-2 text-sm text-white">Reassign 2 crew to NZ78 to protect duty limits.</p>
                  </div>
                  <div className="relative rounded-2xl border border-white/10 bg-white/5 p-4">
                    <p className="text-[11px] uppercase tracking-[0.35em] text-cyan-200/70">Passenger sentiment</p>
                    <p className="mt-2 text-sm text-white">92% of guests already notified via preferred channel.</p>
                    <span className="absolute -right-2 -top-2 inline-flex h-10 w-10 items-center justify-center rounded-full bg-cyan-400/20 text-base font-semibold text-cyan-100 shadow-lg shadow-cyan-500/20">
                      +17%
                    </span>
                  </div>
                </div>
              </div>
              <div className="flex items-center justify-between rounded-3xl border border-white/10 bg-white/5 p-5 text-xs text-slate-300 backdrop-blur">
                <div>
                  <p className="uppercase tracking-[0.4em] text-cyan-200/70">System Health</p>
                  <p className="mt-2 text-sm text-white">Data pipelines nominal · Models synced 4 minutes ago</p>
                </div>
                <div className="relative flex h-14 w-14 items-center justify-center rounded-full border border-cyan-400/20 bg-cyan-500/10">
                  <div className="absolute inset-0 rounded-full border border-cyan-300/40" />
                  <div className="absolute inset-1 rounded-full border border-cyan-200/40" />
                  <span className="relative text-lg font-semibold text-cyan-100">99</span>
                </div>
              </div>
            </div>
          </section>

          <section id="features" className="bg-white/5 py-24">
            <div className="mx-auto max-w-6xl px-6 lg:px-10">
              <div className="mx-auto max-w-3xl text-center">
                <p className="text-xs font-semibold uppercase tracking-[0.4em] text-cyan-200/70">Platform capabilities</p>
                <h2 className="mt-4 text-3xl font-semibold text-white md:text-4xl">
                  Everything your ops center needs in one adaptive surface
                </h2>
                <p className="mt-4 text-base leading-relaxed text-slate-300">
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
                  <p className="text-xs font-semibold uppercase tracking-[0.4em] text-cyan-200/70">Playbook in action</p>
                  <h2 className="mt-4 text-3xl font-semibold text-white md:text-4xl">
                    See how AeroOps guides teams through disruption
                  </h2>
                  <p className="mt-4 text-base leading-relaxed text-slate-300">
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

          <section className="bg-white/5 py-24" id="testimonial">
            <div className="mx-auto max-w-5xl px-6 text-center lg:px-10">
              <div className="relative overflow-hidden rounded-[2.75rem] border border-white/10 bg-gradient-to-br from-slate-900/90 via-slate-950/90 to-black p-10 shadow-2xl shadow-cyan-500/20">
                <div className="absolute -left-24 -top-24 h-72 w-72 rounded-full bg-cyan-500/10 blur-3xl" />
                <div className="absolute -bottom-24 right-10 h-56 w-56 rounded-full bg-sky-500/10 blur-3xl" />
                <div className="relative">
                  <p className="text-lg leading-relaxed text-slate-200 md:text-xl">{testimonial.quote}</p>
                  <div className="mt-8 flex flex-col items-center gap-1 text-sm text-slate-300">
                    <span className="font-semibold text-white">{testimonial.author}</span>
                    <span>{testimonial.role}</span>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section className="py-20">
            <div className="mx-auto max-w-5xl px-6 text-center lg:px-10">
              <p className="text-xs font-semibold uppercase tracking-[0.4em] text-cyan-200/70">Trusted connections</p>
              <div className="mt-8 grid grid-cols-2 gap-6 text-sm text-slate-300 sm:grid-cols-3 md:text-base">
                {integrations.map((logo) => (
                  <div key={logo} className="rounded-2xl border border-white/10 bg-white/5 px-6 py-4 text-center backdrop-blur">
                    {logo}
                  </div>
                ))}
              </div>
            </div>
          </section>

          <section className="pb-24">
            <div className="mx-auto max-w-5xl overflow-hidden rounded-[2.5rem] border border-cyan-400/30 bg-gradient-to-br from-cyan-500/10 via-slate-950 to-slate-950 px-10 py-16 text-center shadow-2xl shadow-cyan-500/30">
              <p className="text-xs font-semibold uppercase tracking-[0.4em] text-cyan-200/80">Ready for wheels up</p>
              <h2 className="mt-4 text-3xl font-semibold text-white md:text-4xl">
                Bring calm to the chaos of airline operations
              </h2>
              <p className="mt-4 text-base leading-relaxed text-slate-300">
                Let AeroOps become your always-on co-strategist—from planning to day-of-execution, across every airport, aircraft, and crew.
              </p>
              <div className="mt-8 flex flex-wrap justify-center gap-4">
                <button className="rounded-full bg-gradient-to-r from-cyan-400 via-sky-500 to-blue-500 px-7 py-3 text-sm font-semibold text-slate-950 shadow-xl shadow-cyan-500/40 transition hover:brightness-110">
                  Schedule a strategy session
                </button>
                <button className="rounded-full border border-white/20 px-7 py-3 text-sm font-semibold text-white/90 backdrop-blur transition hover:border-white/40">
                  Download the product brief
                </button>
              </div>
            </div>
          </section>
        </main>

        <footer className="border-t border-white/10 bg-black/40 py-10">
          <div className="mx-auto flex max-w-6xl flex-col gap-4 px-6 text-xs text-slate-500 sm:flex-row sm:items-center sm:justify-between lg:px-10">
            <p>© {year} AeroOps. Engineered for resilient airline operations.</p>
            <div className="flex gap-6">
              <a href="#features">Platform</a>
              <a href="#workflow">Playbooks</a>
              <a href="#testimonial">Stories</a>
            </div>
          </div>
        </footer>
      </div>
    </div>
  )
}
