import React, { useState } from 'react';

export default function ControlBar({
  simDate, setSimDate, numSims, setNumSims,
  loading, onRunSimulation, onGenerateLineups, onGenerateBrief,
  simResult, contestType, setContestType,
}) {
  const [slateMode, setSlateMode] = useState('quick'); // 'quick' | 'deep'
  const [slateLoading, setSlateLoading] = useState(false);

  const handleTodaysSlate = async () => {
    setSlateLoading(true);
    const sims = slateMode === 'quick' ? 500 : 2000;
    const today = new Date().toISOString().split('T')[0];

    try {
      // Set the date and sims in parent state
      if (setSimDate) setSimDate(today);
      if (setNumSims) setNumSims(sims);

      // Run simulation
      const simRes = await fetch('/api/simulate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ date: today, num_sims: sims }),
      });

      if (simRes.ok) {
        // Generate 20 lineups
        const lineupsRes = await fetch('/api/optimize', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ date: today, num_lineups: 20, contest_type: contestType || 'gpp' }),
        });

        if (lineupsRes.ok) {
          // Trigger parent callbacks to refresh UI
          if (onRunSimulation) onRunSimulation();
        }
      }
    } catch (err) {
      console.error('Slate generation error:', err);
    } finally {
      setSlateLoading(false);
    }
  };

  return (
    <div className="flex gap-3 mb-8 items-center flex-wrap">
      {/* TODAY'S SLATE button group */}
      <div className="flex items-center mr-2">
        {/* Quick/Deep toggle */}
        <div className="flex rounded-l-md overflow-hidden border border-r-0 border-venom/20">
          <button
            onClick={() => setSlateMode('quick')}
            className={`px-3 py-2.5 border-none cursor-pointer text-[10px] font-bold tracking-wider font-mono transition-all ${
              slateMode === 'quick'
                ? 'bg-venom/10 text-venom'
                : 'bg-surface text-text-muted'
            }`}
          >
            QUICK
          </button>
          <button
            onClick={() => setSlateMode('deep')}
            className={`px-3 py-2.5 border-none cursor-pointer text-[10px] font-bold tracking-wider font-mono border-l border-l-venom/20 transition-all ${
              slateMode === 'deep'
                ? 'bg-venom/10 text-venom'
                : 'bg-surface text-text-muted'
            }`}
          >
            DEEP
          </button>
        </div>
        <button
          onClick={handleTodaysSlate}
          disabled={loading || slateLoading}
          className={`px-5 py-2.5 rounded-r-md font-mono text-xs font-extrabold tracking-widest whitespace-nowrap bg-gradient-to-br from-venom to-venom-glow text-primary transition-all cursor-pointer ${
            (loading || slateLoading) ? 'opacity-60' : 'opacity-100'
          }`}
        >
          {slateLoading ? '\u27F3 LOADING...' : 'TODAY\u2019S SLATE \u2192'}
        </button>
      </div>

      {/* Existing controls */}
      <input
        type="date"
        value={simDate}
        onChange={e => setSimDate(e.target.value)}
        className="px-4 py-2.5 bg-surface border border-border/50 rounded-md text-text-primary font-mono text-xs outline-none"
      />
      <select
        value={numSims}
        onChange={e => setNumSims(+e.target.value)}
        className="px-4 py-2.5 bg-surface border border-border/50 rounded-md text-text-primary font-mono text-xs outline-none w-[140px]"
      >
        <option value={500}>Quick (500)</option>
        <option value={2000}>Standard (2K)</option>
        <option value={5000}>Deep (5K)</option>
        <option value={10000}>Ultra (10K)</option>
      </select>
      <select
        value={contestType}
        onChange={e => setContestType(e.target.value)}
        className="px-4 py-2.5 bg-surface border border-border/50 rounded-md text-text-primary font-mono text-xs outline-none w-[110px]"
      >
        <option value="gpp">GPP</option>
        <option value="cash">Cash</option>
      </select>
      <button
        onClick={onRunSimulation}
        disabled={loading}
        className={`px-6 py-2.5 rounded-md font-mono text-xs font-semibold tracking-wider transition-all cursor-pointer bg-gradient-to-br from-venom to-venom-glow text-primary ${
          loading ? 'opacity-50' : 'opacity-100'
        }`}
      >
        {loading ? '\u27F3 SIMULATING...' : '\u25B6 RUN SIMULATION'}
      </button>
      {simResult && (
        <>
          <button
            onClick={onGenerateLineups}
            disabled={loading}
            className="px-6 py-2.5 rounded-md font-mono text-xs font-semibold tracking-wider transition-all cursor-pointer bg-surface2 text-text-muted border border-border/50"
          >
            {'\u26A1'} GENERATE LINEUPS
          </button>
          <button
            onClick={onGenerateBrief}
            disabled={loading}
            className="px-6 py-2.5 rounded-md font-mono text-xs font-semibold tracking-wider transition-all cursor-pointer bg-surface2 text-text-muted border border-border/50"
          >
            {'\uD83E\uDDE0'} AI BRIEF
          </button>
        </>
      )}
    </div>
  );
}
