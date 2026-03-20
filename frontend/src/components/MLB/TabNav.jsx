import React from 'react';

const TABS = ['schedule', 'heatmap', 'projections', 'props', 'lineups', 'stacks', 'intel', 'live', 'portfolio', 'backtest', 'settings'];

export default function TabNav({ tab, setTab }) {
  return (
    <div className="flex mb-8 border-b border-border overflow-x-auto">
      {TABS.map(t => (
        <div
          key={t}
          onClick={() => setTab(t)}
          className={`px-6 py-3 cursor-pointer text-xs tracking-wider uppercase whitespace-nowrap transition-all border-b-2 ${
            tab === t
              ? 'border-venom text-venom'
              : 'border-transparent text-text-muted hover:text-text-primary'
          }`}
        >
          {t}
        </div>
      ))}
    </div>
  );
}
