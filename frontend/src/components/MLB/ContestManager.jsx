import React, { useState } from 'react';

const CONTEST_TYPES = [
  { value: 'cash', label: 'Cash Game', description: 'Floor-optimized, consistent lineups' },
  { value: 'gpp_single', label: 'GPP (Single)', description: 'Ceiling-optimized, one entry' },
  { value: 'gpp_multi', label: 'GPP (Multi)', description: 'Diversified portfolio, multiple entries' },
];

export default function ContestManager({ simResult, onLineups }) {
  const [contests, setContests] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [newContest, setNewContest] = useState({ type: 'gpp_multi', entries: 20, fee: 3 });
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);

  const addContest = () => {
    setContests(prev => [...prev, { ...newContest, id: Date.now() }]);
    setShowModal(false);
    setNewContest({ type: 'gpp_multi', entries: 20, fee: 3 });
  };

  const removeContest = (id) => {
    setContests(prev => prev.filter(c => c.id !== id));
  };

  const totalInvestment = contests.reduce((sum, c) => sum + c.fee * c.entries, 0);

  const optimizePortfolio = async () => {
    if (!contests.length) return;
    setLoading(true);
    try {
      const res = await fetch('/api/optimize/portfolio', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ contests }),
      });
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      setResults(data);
      if (onLineups) onLineups(data);
    } catch (e) {
      console.error('Portfolio optimization failed:', e);
    }
    setLoading(false);
  };

  return (
    <div className="py-5">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-venom m-0 text-base font-bold">
          Contest Portfolio
        </h3>
        <button onClick={() => setShowModal(true)} className="px-4 py-2 rounded-md border border-venom bg-transparent text-venom cursor-pointer text-xs font-semibold font-inherit">
          + Add Contest
        </button>
      </div>

      {/* Contest Cards */}
      {contests.length === 0 ? (
        <div className="text-text-muted text-[13px] text-center py-10">
          No contests added. Click "Add Contest" to build your portfolio.
        </div>
      ) : (
        <div className="grid gap-2.5 mb-4">
          {contests.map(c => {
            const typeInfo = CONTEST_TYPES.find(t => t.value === c.type);
            const lineupCount = results?.[c.type]?.length || 0;
            return (
              <div key={c.id} className="px-[18px] py-3.5 rounded-lg bg-surface border border-border flex justify-between items-center">
                <div>
                  <div className="text-white font-semibold text-[13px]">
                    {typeInfo?.label || c.type}
                  </div>
                  <div className="text-text-muted text-[11px] mt-0.5">
                    {c.entries} entries × ${c.fee} = ${c.entries * c.fee}
                    {lineupCount > 0 && <span className="text-venom ml-2">✓ {lineupCount} lineups</span>}
                  </div>
                </div>
                <button onClick={() => removeContest(c.id)} className="bg-transparent border-none text-red-400 cursor-pointer text-sm">✕</button>
              </div>
            );
          })}
        </div>
      )}

      {/* Summary & Optimize */}
      {contests.length > 0 && (
        <div className="flex justify-between items-center px-[18px] py-3.5 rounded-lg bg-surface border border-border">
          <div>
            <span className="text-text-muted text-[11px]">Total Investment: </span>
            <span className="text-venom font-bold text-base">${totalInvestment}</span>
            <span className="text-text-muted text-[11px] ml-3">
              {contests.reduce((sum, c) => sum + c.entries, 0)} total entries
            </span>
          </div>
          <button onClick={optimizePortfolio} disabled={loading || !simResult}
            className={`px-6 py-2.5 rounded-md border-none font-bold text-[13px] font-inherit ${
              simResult ? 'bg-venom text-black cursor-pointer' : 'bg-text-muted text-black cursor-not-allowed'
            } ${loading ? 'opacity-60' : ''}`}>
            {loading ? 'Optimizing...' : 'Optimize Portfolio'}
          </button>
        </div>
      )}

      {/* Add Contest Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-[2000]" onClick={() => setShowModal(false)}>
          <div className="bg-primary border border-border rounded-xl p-6 w-[360px]" onClick={e => e.stopPropagation()}>
            <h3 className="text-venom m-0 mb-4 text-base">Add Contest</h3>

            <div className="mb-3.5">
              <label className="text-text-muted text-[11px] block mb-1">Contest Type</label>
              <select value={newContest.type} onChange={e => setNewContest(prev => ({ ...prev, type: e.target.value }))}
                className="w-full px-3 py-2 rounded-md bg-surface border border-border text-text-primary text-[13px] font-inherit">
                {CONTEST_TYPES.map(t => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>

            <div className="flex gap-3 mb-4">
              <div className="flex-1">
                <label className="text-text-muted text-[11px] block mb-1">Entries</label>
                <input type="number" min="1" max="150" value={newContest.entries}
                  onChange={e => setNewContest(prev => ({ ...prev, entries: parseInt(e.target.value) || 1 }))}
                  className="w-full px-3 py-2 rounded-md bg-surface border border-border text-text-primary text-[13px] font-inherit box-border" />
              </div>
              <div className="flex-1">
                <label className="text-text-muted text-[11px] block mb-1">Entry Fee ($)</label>
                <input type="number" min="0.25" step="0.25" value={newContest.fee}
                  onChange={e => setNewContest(prev => ({ ...prev, fee: parseFloat(e.target.value) || 0 }))}
                  className="w-full px-3 py-2 rounded-md bg-surface border border-border text-text-primary text-[13px] font-inherit box-border" />
              </div>
            </div>

            <div className="flex gap-2.5 justify-end">
              <button onClick={() => setShowModal(false)} className="px-4 py-2 rounded-md border border-border bg-transparent text-text-muted cursor-pointer text-xs font-inherit">Cancel</button>
              <button onClick={addContest} className="px-4 py-2 rounded-md border-none bg-venom text-black font-bold cursor-pointer text-xs font-inherit">Add</button>
            </div>
          </div>
        </div>
      )}

      {/* Results Summary */}
      {results?._summary && (
        <div className="mt-4 px-[18px] py-3.5 rounded-lg bg-surface border border-venom/20">
          <div className="text-venom text-xs font-bold mb-2">
            Portfolio Summary
          </div>
          <div className="grid grid-cols-3 gap-2.5 text-xs">
            <div>
              <span className="text-text-muted">Total Lineups: </span>
              <span className="text-white font-semibold">{results._summary.total_lineups}</span>
            </div>
            <div>
              <span className="text-text-muted">Unique Players: </span>
              <span className="text-white font-semibold">{results._summary.unique_players}</span>
            </div>
            <div>
              <span className="text-text-muted">Investment: </span>
              <span className="text-venom font-semibold">${results._summary.total_investment}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
