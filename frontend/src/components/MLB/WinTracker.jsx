import React, { useState, useEffect, useMemo, useCallback } from 'react';

const STORAGE_KEY = 'stacksniper_results';

function loadResults() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveResults(results) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(results));
}

async function postResultToServer(entry) {
  try {
    const token = localStorage.getItem('stacksniper_token');
    if (!token) return;
    await fetch('/api/results/log', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(entry),
    });
  } catch {
    // Silently fail — localStorage is the primary store
  }
}

function formatCurrency(val) {
  const n = Number(val);
  if (isNaN(n)) return '$0.00';
  const sign = n < 0 ? '-' : '';
  return `${sign}$${Math.abs(n).toFixed(2)}`;
}

function MiniLineChart({ data, width, height, color, negColor }) {
  if (!data || data.length < 2) {
    return (
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
        <text x={width / 2} y={height / 2} textAnchor="middle" fill="#555" fontSize="12">
          Need 2+ results to chart
        </text>
      </svg>
    );
  }

  const padding = { top: 10, right: 10, bottom: 10, left: 10 };
  const chartW = width - padding.left - padding.right;
  const chartH = height - padding.top - padding.bottom;

  const minY = Math.min(0, ...data);
  const maxY = Math.max(0, ...data);
  const range = maxY - minY || 1;

  const points = data.map((v, i) => {
    const x = padding.left + (i / (data.length - 1)) * chartW;
    const y = padding.top + chartH - ((v - minY) / range) * chartH;
    return { x, y, v };
  });

  const pathD = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ');

  const zeroY = padding.top + chartH - ((0 - minY) / range) * chartH;
  const lastVal = data[data.length - 1];
  const lineColor = lastVal >= 0 ? color : negColor;

  // Gradient fill
  const fillPoints = [
    ...points.map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`),
    `${points[points.length - 1].x.toFixed(1)},${zeroY.toFixed(1)}`,
    `${points[0].x.toFixed(1)},${zeroY.toFixed(1)}`,
  ].join(' ');

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
      <defs>
        <linearGradient id="plGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={lineColor} stopOpacity="0.3" />
          <stop offset="100%" stopColor={lineColor} stopOpacity="0.02" />
        </linearGradient>
      </defs>
      {/* Zero line */}
      <line
        x1={padding.left} y1={zeroY} x2={width - padding.right} y2={zeroY}
        stroke="#333" strokeWidth="1" strokeDasharray="4 3"
      />
      {/* Fill area */}
      <polygon points={fillPoints} fill="url(#plGrad)" />
      {/* Line */}
      <path d={pathD} fill="none" stroke={lineColor} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      {/* Data points */}
      {points.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r="3" fill={p.v >= 0 ? color : negColor} stroke="#0a0e17" strokeWidth="1.5" />
      ))}
    </svg>
  );
}

export default function WinTracker() {
  const [results, setResults] = useState(loadResults);
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [contestName, setContestName] = useState('');
  const [entryFee, setEntryFee] = useState('');
  const [payout, setPayout] = useState('');
  const [sortKey, setSortKey] = useState('date');
  const [sortDir, setSortDir] = useState(-1);

  useEffect(() => {
    saveResults(results);
  }, [results]);

  const handleLog = useCallback(() => {
    const fee = parseFloat(entryFee) || 0;
    const pay = parseFloat(payout) || 0;
    if (!contestName.trim()) return;

    const entry = {
      id: Date.now().toString(36) + Math.random().toString(36).slice(2, 6),
      date,
      contest: contestName.trim(),
      fee,
      payout: pay,
      net: pay - fee,
      timestamp: new Date().toISOString(),
    };

    setResults(prev => [...prev, entry]);
    postResultToServer(entry);
    setContestName('');
    setEntryFee('');
    setPayout('');
  }, [date, contestName, entryFee, payout]);

  const handleDelete = useCallback((id) => {
    setResults(prev => prev.filter(r => r.id !== id));
  }, []);

  const stats = useMemo(() => {
    const totalInvested = results.reduce((s, r) => s + r.fee, 0);
    const totalWon = results.reduce((s, r) => s + r.payout, 0);
    const netPL = totalWon - totalInvested;
    const roi = totalInvested > 0 ? (netPL / totalInvested) * 100 : 0;
    const wins = results.filter(r => r.net > 0).length;
    const winRate = results.length > 0 ? (wins / results.length) * 100 : 0;
    return { totalInvested, totalWon, netPL, roi, winRate, wins, total: results.length };
  }, [results]);

  const cumulativePL = useMemo(() => {
    const sorted = [...results].sort((a, b) => a.date.localeCompare(b.date) || a.timestamp.localeCompare(b.timestamp));
    let running = 0;
    return sorted.map(r => {
      running += r.net;
      return running;
    });
  }, [results]);

  const sortedResults = useMemo(() => {
    return [...results].sort((a, b) => {
      let aVal = a[sortKey];
      let bVal = b[sortKey];
      if (typeof aVal === 'string') return aVal.localeCompare(bVal) * sortDir;
      return (aVal - bVal) * sortDir;
    });
  }, [results, sortKey, sortDir]);

  const handleSort = (key) => {
    if (sortKey === key) {
      setSortDir(d => d * -1);
    } else {
      setSortKey(key);
      setSortDir(-1);
    }
  };

  const summaryCards = [
    { label: 'Total Invested', value: formatCurrency(stats.totalInvested), colorClass: 'text-text-muted' },
    { label: 'Total Won', value: formatCurrency(stats.totalWon), colorClass: 'text-venom' },
    { label: 'Net P&L', value: formatCurrency(stats.netPL), colorClass: stats.netPL >= 0 ? 'text-venom' : 'text-red-500' },
    { label: 'ROI', value: `${stats.roi >= 0 ? '+' : ''}${stats.roi.toFixed(1)}%`, colorClass: stats.roi >= 0 ? 'text-venom' : 'text-red-500' },
    { label: 'Win Rate', value: `${stats.winRate.toFixed(1)}%`, colorClass: stats.winRate >= 50 ? 'text-venom' : 'text-text-muted' },
  ];

  const columns = [
    { key: 'date', label: 'Date' },
    { key: 'contest', label: 'Contest' },
    { key: 'fee', label: 'Fee' },
    { key: 'payout', label: 'Payout' },
    { key: 'net', label: 'Net' },
  ];

  return (
    <div className="p-5 max-w-[1000px] mx-auto">
      {/* Form */}
      <div className="bg-surface rounded-xl px-6 py-5 border border-border mb-5">
        <div className="text-[15px] font-bold text-venom mb-3.5 tracking-wider">
          LOG CONTEST RESULT
        </div>
        <div className="flex gap-2.5 flex-wrap items-end">
          <div className="flex flex-col gap-1">
            <label className="text-[10px] text-text-muted tracking-wider uppercase">Date</label>
            <input
              type="date"
              value={date}
              onChange={e => setDate(e.target.value)}
              className="px-3 py-2 bg-surface2 border border-border rounded-md text-text-primary font-mono text-[13px] outline-none w-[150px]"
              style={{ colorScheme: 'dark' }}
            />
          </div>
          <div className="flex flex-col gap-1 flex-1 min-w-[160px]">
            <label className="text-[10px] text-text-muted tracking-wider uppercase">Contest Name</label>
            <input
              type="text"
              value={contestName}
              onChange={e => setContestName(e.target.value)}
              placeholder="e.g. DK $5 GPP"
              className="px-3 py-2 bg-surface2 border border-border rounded-md text-text-primary font-mono text-[13px] outline-none"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-[10px] text-text-muted tracking-wider uppercase">Entry Fee</label>
            <input
              type="number"
              value={entryFee}
              onChange={e => setEntryFee(e.target.value)}
              placeholder="$0.00"
              min="0"
              step="0.01"
              className="px-3 py-2 bg-surface2 border border-border rounded-md text-text-primary font-mono text-[13px] outline-none w-[100px]"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-[10px] text-text-muted tracking-wider uppercase">Payout</label>
            <input
              type="number"
              value={payout}
              onChange={e => setPayout(e.target.value)}
              placeholder="$0.00"
              min="0"
              step="0.01"
              className="px-3 py-2 bg-surface2 border border-border rounded-md text-text-primary font-mono text-[13px] outline-none w-[100px]"
            />
          </div>
          <button
            onClick={handleLog}
            disabled={!contestName.trim()}
            className={`px-5 py-2.5 border-none rounded-md font-bold text-xs tracking-wider font-mono whitespace-nowrap transition-all ${
              contestName.trim()
                ? 'bg-gradient-to-br from-venom to-venom-glow text-primary cursor-pointer'
                : 'bg-surface2 text-text-muted cursor-default'
            }`}
          >
            LOG RESULT
          </button>
        </div>
      </div>

      {/* P&L Chart */}
      <div className="bg-surface rounded-xl px-6 py-5 border border-border mb-5">
        <div className="text-[13px] font-semibold text-text-muted mb-3 tracking-wider">
          CUMULATIVE P&L
        </div>
        <MiniLineChart data={cumulativePL} width={940} height={160} color="#39FF14" negColor="#ff4444" />
      </div>

      {/* Summary Cards */}
      <div className="flex gap-3 flex-wrap mb-5">
        {summaryCards.map(card => (
          <div key={card.label} className="bg-surface rounded-lg px-5 py-4 border border-border flex-1 min-w-[140px]">
            <div className="text-[10px] text-text-muted tracking-wider uppercase mb-1.5">
              {card.label}
            </div>
            <div className={`text-[22px] font-extrabold font-mono ${card.colorClass}`}>
              {card.value}
            </div>
          </div>
        ))}
      </div>

      {/* Results Table */}
      <div className="bg-surface rounded-xl border border-border overflow-hidden">
        <div className="px-5 pt-4 pb-2 text-[13px] font-semibold text-text-muted tracking-wider">
          RESULTS ({results.length})
        </div>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr>
                {columns.map(col => (
                  <th
                    key={col.key}
                    onClick={() => handleSort(col.key)}
                    className={`px-4 py-2.5 text-[10px] font-semibold tracking-wider uppercase border-b border-border cursor-pointer select-none whitespace-nowrap ${
                      col.key === 'contest' ? 'text-left' : 'text-right'
                    } ${sortKey === col.key ? 'text-venom' : 'text-text-muted'}`}
                  >
                    {col.label} {sortKey === col.key ? (sortDir === 1 ? '\u25B2' : '\u25BC') : ''}
                  </th>
                ))}
                <th className="w-10 border-b border-border" />
              </tr>
            </thead>
            <tbody>
              {sortedResults.length === 0 ? (
                <tr>
                  <td colSpan={6} className="p-8 text-center text-text-muted text-[13px]">
                    No results logged yet. Enter your first contest result above.
                  </td>
                </tr>
              ) : (
                sortedResults.map(r => {
                  const isWin = r.net > 0;
                  const netColorClass = isWin ? 'text-venom' : r.net < 0 ? 'text-red-500' : 'text-text-muted';
                  return (
                    <tr key={r.id} className="border-b border-border/5">
                      <td className="px-4 py-2.5 text-right text-xs text-text-muted font-mono">
                        {r.date}
                      </td>
                      <td className="px-4 py-2.5 text-[13px] text-text-primary">
                        {r.contest}
                      </td>
                      <td className="px-4 py-2.5 text-right text-xs text-text-muted font-mono">
                        {formatCurrency(r.fee)}
                      </td>
                      <td className="px-4 py-2.5 text-right text-xs text-venom font-mono">
                        {formatCurrency(r.payout)}
                      </td>
                      <td className={`px-4 py-2.5 text-right text-[13px] font-bold font-mono ${netColorClass}`}>
                        {r.net >= 0 ? '+' : ''}{formatCurrency(r.net)}
                      </td>
                      <td className="px-2 py-2.5 text-center">
                        <button
                          onClick={() => handleDelete(r.id)}
                          className="bg-transparent border-none text-text-muted/40 cursor-pointer text-sm px-1.5 py-0.5 rounded hover:text-text-muted"
                          title="Delete result"
                        >
                          ×
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
