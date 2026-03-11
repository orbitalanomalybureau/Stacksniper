import { Link } from "react-router-dom";
import { Cpu, ListOrdered, TrendingUp, ChevronDown, Check, Zap, Shield, Crown } from "lucide-react";
import { Disclosure, DisclosureButton, DisclosurePanel } from "@headlessui/react";
import Logo from "../components/Logo";

const FEATURES = [
  {
    icon: TrendingUp,
    title: "Smart Projections",
    desc: "ML-driven point projections with floor/ceiling ranges and statistical distributions for every NFL player.",
  },
  {
    icon: Cpu,
    title: "Monte Carlo Sims",
    desc: "Run 10,000+ correlated simulations to understand true outcome distributions and find hidden edges.",
  },
  {
    icon: ListOrdered,
    title: "Lineup Optimizer",
    desc: "Generate salary-cap-optimal lineups using integer linear programming with correlation-aware stacking.",
  },
];

const STATS = [
  { value: "50M+", label: "Simulations Run" },
  { value: "10K+", label: "Lineups Optimized" },
  { value: "7", label: "Position Groups" },
  { value: "18", label: "NFL Weeks" },
];

const PLANS = [
  {
    name: "Free",
    price: "$0",
    features: ["Basic projections", "5 sims/week (1K max)", "3 lineups"],
    cta: "Start Free",
    style: "border-border",
  },
  {
    name: "Pro",
    price: "$19",
    period: "/mo",
    features: ["Floor/ceiling ranges", "100 sims/week (5K max)", "50 lineups", "CSV export"],
    cta: "Go Pro",
    style: "border-venom ring-1 ring-venom/30",
    badge: true,
  },
  {
    name: "Elite",
    price: "$49",
    period: "/mo",
    features: ["Full stat breakdowns", "Unlimited sims (10K)", "150 lineups", "Priority support"],
    cta: "Go Elite",
    style: "border-gold/40",
  },
];

const FAQS = [
  {
    q: "How do the projections work?",
    a: "Our projections combine multiple statistical models, injury reports, weather data, and Vegas lines to produce floor/ceiling ranges for every player.",
  },
  {
    q: "What is a Monte Carlo simulation?",
    a: "Monte Carlo simulations run thousands of randomized scenarios using correlated player distributions to model the full range of possible DFS outcomes.",
  },
  {
    q: "Can I use this for DraftKings and FanDuel?",
    a: "Yes. We support both DraftKings and FanDuel salary structures, scoring rules, and lineup constraints.",
  },
  {
    q: "Is there a free trial?",
    a: "The Free tier is free forever with limited features. Pro plans include a 7-day free trial with full access.",
  },
];

export default function Home() {
  return (
    <div>
      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 flex items-center justify-center opacity-5 pointer-events-none">
          <Logo size={600} className="animate-crosshair-spin" />
        </div>
        <div className="relative max-w-7xl mx-auto px-4 py-24 md:py-32 text-center">
          <h1 className="text-5xl md:text-7xl font-black mb-6 tracking-tight">
            <span className="bg-gradient-to-r from-venom to-venom-glow bg-clip-text text-transparent">
              Snipe
            </span>{" "}
            the Stack.
          </h1>
          <p className="text-xl md:text-2xl text-text-secondary max-w-2xl mx-auto mb-10 font-light">
            AI-powered NFL DFS projections, Monte Carlo simulations, and lineup
            optimization. Built for serious grinders.
          </p>
          <div className="flex gap-4 justify-center flex-wrap">
            <Link to="/register" className="btn-primary btn-lg">
              Start Free
            </Link>
            <Link to="/pricing" className="btn-secondary btn-lg">
              View Plans
            </Link>
          </div>
        </div>
      </section>

      {/* Stats Bar */}
      <section className="border-y border-border bg-surface2/50">
        <div className="max-w-7xl mx-auto px-4 py-8 grid grid-cols-2 md:grid-cols-4 gap-6">
          {STATS.map((s) => (
            <div key={s.label} className="text-center">
              <p className="text-2xl md:text-3xl font-bold text-venom font-mono">{s.value}</p>
              <p className="text-sm text-text-muted mt-1">{s.label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="max-w-7xl mx-auto px-4 py-20">
        <h2 className="text-3xl font-bold text-center mb-12">Your DFS Arsenal</h2>
        <div className="grid md:grid-cols-3 gap-8">
          {FEATURES.map(({ icon: Icon, title, desc }) => (
            <div key={title} className="card-hover text-center py-8">
              <div className="w-14 h-14 rounded-xl bg-venom/10 flex items-center justify-center mx-auto mb-5">
                <Icon className="w-7 h-7 text-venom" />
              </div>
              <h3 className="text-lg font-semibold mb-3">{title}</h3>
              <p className="text-text-muted text-sm leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Pricing Preview */}
      <section className="bg-surface/50 border-y border-border">
        <div className="max-w-5xl mx-auto px-4 py-20">
          <h2 className="text-3xl font-bold text-center mb-4">Choose Your Edge</h2>
          <p className="text-text-muted text-center mb-12">Scale your DFS game with the right plan.</p>
          <div className="grid md:grid-cols-3 gap-6">
            {PLANS.map((plan) => (
              <div key={plan.name} className={`card-hover text-center border ${plan.style}`}>
                {plan.badge && (
                  <div className="absolute top-0 left-0 right-0">
                    <span className="inline-block bg-venom text-primary text-xs font-bold px-3 py-1 rounded-b-lg">
                      POPULAR
                    </span>
                  </div>
                )}
                <div className="pt-2">
                  <h3 className="text-lg font-semibold mb-2">{plan.name}</h3>
                  <p className="text-3xl font-black text-venom">
                    {plan.price}
                    {plan.period && <span className="text-sm font-normal text-text-muted">{plan.period}</span>}
                  </p>
                  <ul className="mt-6 space-y-2 text-sm text-text-secondary text-left">
                    {plan.features.map((f) => (
                      <li key={f} className="flex items-center gap-2">
                        <Check className="w-4 h-4 text-venom flex-shrink-0" />
                        {f}
                      </li>
                    ))}
                  </ul>
                  <Link
                    to="/register"
                    className={`mt-6 block w-full text-center py-2 rounded-lg text-sm font-semibold transition-colors ${
                      plan.badge
                        ? "btn-primary"
                        : "border border-border text-text-secondary hover:border-venom hover:text-venom"
                    }`}
                  >
                    {plan.cta}
                  </Link>
                </div>
              </div>
            ))}
          </div>
          <div className="text-center mt-8">
            <Link to="/pricing" className="text-venom hover:underline text-sm">
              View full plan details &rarr;
            </Link>
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="max-w-3xl mx-auto px-4 py-20">
        <h2 className="text-3xl font-bold text-center mb-12">FAQ</h2>
        <div className="space-y-3">
          {FAQS.map(({ q, a }) => (
            <Disclosure key={q}>
              {({ open }) => (
                <div className="card !p-0 overflow-hidden">
                  <DisclosureButton className="w-full flex items-center justify-between px-6 py-4 text-left hover:bg-surface/50 transition-colors">
                    <span className="font-medium text-text-primary">{q}</span>
                    <ChevronDown
                      className={`w-5 h-5 text-text-muted transition-transform duration-200 flex-shrink-0 ${
                        open ? "rotate-180" : ""
                      }`}
                    />
                  </DisclosureButton>
                  <DisclosurePanel className="px-6 pb-4 text-text-muted text-sm leading-relaxed">
                    {a}
                  </DisclosurePanel>
                </div>
              )}
            </Disclosure>
          ))}
        </div>
      </section>

      {/* Bottom CTA */}
      <section className="max-w-7xl mx-auto px-4 py-20 text-center">
        <h2 className="text-3xl font-bold mb-4">Ready to Snipe?</h2>
        <p className="text-text-muted mb-8">Start with our free tier. No credit card required.</p>
        <Link to="/register" className="btn-primary btn-lg">
          Create Free Account
        </Link>
      </section>
    </div>
  );
}
