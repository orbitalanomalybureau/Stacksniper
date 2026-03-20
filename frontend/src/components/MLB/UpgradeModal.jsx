import React, { useState } from 'react';

const FEATURE_CONFIG = {
  optimizer: {
    title: 'Unlock Lineup Optimizer',
    description: 'Turn projections into winning lineups with our constraint-based optimizer',
    icon: '\uD83C\uDFAF',
  },
  copilot: {
    title: 'Unlock AI Co-Pilot',
    description: 'Ask any question about today\'s slate and get data-backed answers',
    icon: '\uD83E\uDD16',
  },
  showdown: {
    title: 'Unlock Showdown Mode',
    description: 'Dominate single-game contests with specialized analysis',
    icon: '\u26A1',
  },
  brief: {
    title: 'Unlock Intel Briefs',
    description: 'AI-generated game narratives with injury and weather impacts',
    icon: '\uD83D\uDCCA',
  },
  export: {
    title: 'Unlock CSV Export',
    description: 'Export optimized lineups directly to DraftKings',
    icon: '\uD83D\uDCE5',
  },
  backtest: {
    title: 'Unlock Backtesting',
    description: 'Test strategies against historical data',
    icon: '\uD83D\uDCC8',
  },
};

const PLAN_FEATURES = [
  { name: 'Monte Carlo Simulations', free: '500 sims', pro: '5,000 sims', elite: '10,000 sims' },
  { name: 'Lineup Optimizer', free: '\u2014', pro: '\u2713', elite: '\u2713' },
  { name: 'AI Co-Pilot', free: '\u2014', pro: '\u2713', elite: '\u2713' },
  { name: 'Showdown Mode', free: '\u2014', pro: '\u2014', elite: '\u2713' },
  { name: 'Intel Briefs', free: '\u2014', pro: '\u2713', elite: '\u2713' },
  { name: 'CSV Export', free: '\u2014', pro: '\u2713', elite: '\u2713' },
  { name: 'Backtesting', free: '\u2014', pro: '\u2014', elite: '\u2713' },
  { name: 'Priority Support', free: '\u2014', pro: '\u2014', elite: '\u2713' },
];

function FeatureRow({ feature, isLast }) {
  return (
    <div className={`grid grid-cols-[1.6fr_0.8fr_0.8fr_0.8fr] py-2.5 text-xs ${
      isLast ? '' : 'border-b border-border'
    }`}>
      <div className="text-text-muted">{feature.name}</div>
      <div className="text-text-muted text-center">{feature.free}</div>
      <div className={`text-center ${feature.pro === '\u2713' ? 'text-venom font-bold' : 'text-text-muted'}`}>{feature.pro}</div>
      <div className={`text-center ${feature.elite === '\u2713' ? 'text-venom-glow font-bold' : 'text-text-muted'}`}>{feature.elite}</div>
    </div>
  );
}

export default function UpgradeModal({ isOpen, onClose, feature, requiredTier }) {
  const [loading, setLoading] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState(requiredTier === 'elite' ? 'elite' : 'pro');

  if (!isOpen) return null;

  const config = FEATURE_CONFIG[feature] || {
    title: 'Unlock This Feature',
    description: 'Upgrade your plan to access this feature.',
    icon: '\uD83D\uDD12',
  };

  const handleStartTrial = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('stacksniper_token');
      const headers = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;

      const res = await fetch('/api/billing/create-checkout', {
        method: 'POST',
        headers,
        body: JSON.stringify({ plan: selectedPlan, trial: true }),
      });

      if (res.ok) {
        const data = await res.json();
        if (data.checkout_url) {
          window.location.href = data.checkout_url;
        }
      }
    } catch (err) {
      console.error('Checkout error:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      onClick={onClose}
      className="fixed inset-0 bg-black/80 z-[10000] flex items-center justify-center"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="bg-primary rounded-xl border border-border max-w-[580px] w-[92%] max-h-[90vh] overflow-y-auto shadow-2xl"
      >
        {/* Header */}
        <div className="px-8 pt-8 pb-6 text-center border-b border-border">
          <div className="text-5xl mb-3">{config.icon}</div>
          <h2 className="text-text-primary text-[22px] font-bold mb-2">
            {config.title}
          </h2>
          <p className="text-text-muted text-sm leading-relaxed m-0">
            {config.description}
          </p>
        </div>

        {/* Pricing cards */}
        <div className="px-8 py-6 flex gap-3">
          {/* Pro */}
          <div
            onClick={() => setSelectedPlan('pro')}
            className={`flex-1 p-5 rounded-lg cursor-pointer transition-all duration-200 border-2 ${
              selectedPlan === 'pro'
                ? 'bg-venom/5 border-venom'
                : 'bg-surface border-border'
            }`}
          >
            <div className="text-[11px] font-bold tracking-[2px] text-venom mb-2 uppercase">
              PRO
            </div>
            <div className="flex items-baseline gap-0.5">
              <span className="text-text-primary text-[32px] font-extrabold">$29</span>
              <span className="text-text-muted text-[13px]">/mo</span>
            </div>
            <div className="text-text-muted text-xs mt-2">
              Optimizer, Co-Pilot, Briefs, Export
            </div>
          </div>

          {/* Elite */}
          <div
            onClick={() => setSelectedPlan('elite')}
            className={`flex-1 p-5 rounded-lg cursor-pointer transition-all duration-200 border-2 relative ${
              selectedPlan === 'elite'
                ? 'bg-venom-glow/5 border-venom-glow'
                : 'bg-surface border-border'
            }`}
          >
            <div className="absolute -top-2.5 right-3 bg-venom-glow text-primary text-[9px] font-extrabold px-2.5 py-0.5 rounded-full tracking-wider">
              BEST VALUE
            </div>
            <div className="text-[11px] font-bold tracking-[2px] text-venom-glow mb-2 uppercase">
              ELITE
            </div>
            <div className="flex items-baseline gap-0.5">
              <span className="text-text-primary text-[32px] font-extrabold">$79</span>
              <span className="text-text-muted text-[13px]">/mo</span>
            </div>
            <div className="text-text-muted text-xs mt-2">
              Everything + Showdown, Backtest, Priority
            </div>
          </div>
        </div>

        {/* Feature comparison table */}
        <div className="px-8 pb-4">
          <div className="bg-surface2 rounded-lg p-4 border border-border">
            <div className="grid grid-cols-[1.6fr_0.8fr_0.8fr_0.8fr] pb-2 mb-1 border-b border-border">
              <div className="text-[10px] text-text-muted font-bold tracking-wider uppercase">Feature</div>
              <div className="text-[10px] text-text-muted font-bold tracking-wider uppercase text-center">Free</div>
              <div className="text-[10px] text-venom font-bold tracking-wider uppercase text-center">Pro</div>
              <div className="text-[10px] text-venom-glow font-bold tracking-wider uppercase text-center">Elite</div>
            </div>
            {PLAN_FEATURES.map((f, i) => (
              <FeatureRow key={f.name} feature={f} isLast={i === PLAN_FEATURES.length - 1} />
            ))}
          </div>
        </div>

        {/* CTA */}
        <div className="px-8 pt-4 pb-8 text-center">
          <button
            onClick={handleStartTrial}
            disabled={loading}
            className={`w-full py-3.5 rounded-lg border-none text-sm font-extrabold cursor-pointer tracking-wider transition-all duration-200 ${
              loading ? 'opacity-70 cursor-wait' : 'opacity-100'
            } ${
              selectedPlan === 'elite'
                ? 'bg-gradient-to-br from-venom-glow to-green-600 text-primary'
                : 'bg-gradient-to-br from-venom to-venom-glow text-primary'
            }`}
          >
            {loading ? 'LOADING...' : `START 7-DAY FREE TRIAL \u2014 ${selectedPlan === 'elite' ? 'ELITE' : 'PRO'}`}
          </button>
          <button
            onClick={onClose}
            className="bg-transparent border-none text-text-muted text-[13px] cursor-pointer mt-4 px-2 py-1"
          >
            Maybe Later
          </button>
        </div>
      </div>
    </div>
  );
}
