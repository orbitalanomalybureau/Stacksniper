import React, { useState } from 'react';

const API = '/api';

function MetricCard({ label, value, color, subtitle }) {
  const colorClass = color || 'text-venom';
  return (
    <div className="bg-surface rounded-lg p-5 border border-border">
      <div className="text-text-muted text-[10px] tracking-[2px] uppercase mb-1.5">
        {label}
      </div>
      <div className={`text-2xl font-extrabold ${colorClass}`}>
        {value}
      </div>
      {subtitle && (
        <div className="text-[10px] text-text-muted mt-1">{subtitle}</div>
      )}
    </div>
  );
}

function PositionTable({ byPosition }) {
  if (!byPosition || Object.keys(byPosition).length === 0) return null;
  const positions = Object.entries(byPosition).sort((a, b) => b[1].count - a[1].count);

  return (
    <div className="bg-surface rounded-lg p-5 border border-border mt-4">
      <div className="text-xs text-venom tracking-widest uppercase mb-3 font-semibold">Accuracy by Position</div>
      <table className="w-full border-collapse text-xs">
        <thead>
          <tr>
            {['Position', 'Players', 'MAE', 'Correlation', 'Avg Proj', 'Avg Actual', 'Bias'].map(h => (
              <th key={h} className="text-left px-3 py-2.5 border-b border-border/50 text-text-muted text-[10px] tracking-wider uppercase whitespace-nowrap">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {positions.map(([pos, data]) => (
            <tr key={pos}>
              <td className="px-3 py-2 border-b border-border/30 whitespace-nowrap">
                <span className="inline-block px-2 py-0.5 rounded-full text-[10px] font-semibold bg-primary text-blue-400">{pos}</span>
              </td>
              <td className="px-3 py-2 border-b border-border/30 whitespace-nowrap">{data.count}</td>
              <td className="px-3 py-2 border-b border-border/30 whitespace-nowrap">{data.mae}</td>
              <td className={`px-3 py-2 border-b border-border/30 whitespace-nowrap ${data.correlation > 0.3 ? 'text-venom' : data.correlation > 0.15 ? 'text-orange-400' : 'text-venom'}`}>
                {data.correlation}
              </td>
              <td className="px-3 py-2 border-b border-border/30 whitespace-nowrap">{data.avg_projected}</td>
              <td className="px-3 py-2 border-b border-border/30 whitespace-nowrap">{data.avg_actual}</td>
              <td className={`px-3 py-2 border-b border-border/30 whitespace-nowrap ${Math.abs(data.bias) > 2 ? 'text-venom' : Math.abs(data.bias) > 1 ? 'text-orange-400' : 'text-venom'}`}>
                {data.bias > 0 ? '+' : ''}{data.bias}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DateResults({ byDate }) {
  if (!byDate || byDate.length === 0) return null;

  return (
    <div className="bg-surface rounded-lg p-5 border border-border mt-4">
      <div className="text-xs text-venom tracking-widest uppercase mb-3 font-semibold">Results by Date</div>
      <table className="w-full border-collapse text-xs">
        <thead>
          <tr>
            {['Date', 'Players', 'MAE', 'RMSE', 'Corr', 'Hit 10%', 'Hit 20%', 'Top-10', 'Ceil %', 'Floor Miss %'].map(h => (
              <th key={h} className="text-left px-3 py-2.5 border-b border-border/50 text-text-muted text-[10px] tracking-wider uppercase whitespace-nowrap">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {byDate.map(r => (
            <tr key={r.date}>
              <td className="px-3 py-2 border-b border-border/30 whitespace-nowrap text-blue-400">{r.date}</td>
              <td className="px-3 py-2 border-b border-border/30 whitespace-nowrap">{r.num_players}</td>
              <td className="px-3 py-2 border-b border-border/30 whitespace-nowrap">{r.mae}</td>
              <td className="px-3 py-2 border-b border-border/30 whitespace-nowrap">{r.rmse}</td>
              <td className={`px-3 py-2 border-b border-border/30 whitespace-nowrap ${r.correlation > 0.3 ? 'text-venom' : 'text-text-muted'}`}>
                {r.correlation}
              </td>
              <td className="px-3 py-2 border-b border-border/30 whitespace-nowrap">{r.hit_rate_10pct}%</td>
              <td className="px-3 py-2 border-b border-border/30 whitespace-nowrap">{r.hit_rate_20pct}%</td>
              <td className="px-3 py-2 border-b border-border/30 whitespace-nowrap">{r.top10_overlap}%</td>
              <td className="px-3 py-2 border-b border-border/30 whitespace-nowrap">{r.ceiling_hit_rate}%</td>
              <td className="px-3 py-2 border-b border-border/30 whitespace-nowrap">{r.floor_miss_rate}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function BacktestView() {
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [numSims, setNumSims] = useState(300);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const runBacktest = async () => {
    if (!startDate) {
      setError('Start date is required');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API}/backtest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          start_date: startDate,
          end_date: endDate || startDate,
          num_sims: numSims,
        }),
      });
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      setResult(data);
    } catch (e) {
      setError('Backtest failed: ' + e.message);
    }
    setLoading(false);
  };

  const runCalibrate = async () => {
    if (!startDate) {
      setError('Start date is required');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API}/backtest/calibrate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          start_date: startDate,
          end_date: endDate || startDate,
          num_sims: numSims,
        }),
      });
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      setResult(prev => ({ ...prev, calibration: data }));
    } catch (e) {
      setError('Calibration failed: ' + e.message);
    }
    setLoading(false);
  };

  return (
    <div>
      {/* Controls */}
      <div className="flex gap-3 mb-6 items-center flex-wrap">
        <div>
          <label className="text-[10px] text-text-muted block mb-1 tracking-[1px] uppercase">
            Start Date
          </label>
          <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} className="px-4 py-2.5 bg-surface border border-border/50 rounded-md text-text-primary font-mono text-xs outline-none" />
        </div>
        <div>
          <label className="text-[10px] text-text-muted block mb-1 tracking-[1px] uppercase">
            End Date
          </label>
          <input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} className="px-4 py-2.5 bg-surface border border-border/50 rounded-md text-text-primary font-mono text-xs outline-none" />
        </div>
        <div>
          <label className="text-[10px] text-text-muted block mb-1 tracking-[1px] uppercase">
            Sims/Date
          </label>
          <select value={numSims} onChange={e => setNumSims(+e.target.value)} className="px-4 py-2.5 bg-surface border border-border/50 rounded-md text-text-primary font-mono text-xs outline-none w-[120px]">
            <option value={100}>Quick (100)</option>
            <option value={300}>Standard (300)</option>
            <option value={500}>Deep (500)</option>
          </select>
        </div>
        <div className="self-end">
          <button onClick={runBacktest} disabled={loading} className={`px-6 py-2.5 rounded-md font-mono text-xs font-semibold tracking-wider transition-all cursor-pointer bg-gradient-to-br from-venom to-venom-glow text-primary ${loading ? 'opacity-50' : ''}`}>
            {loading ? '\u27F3 RUNNING...' : '\u25B6 RUN BACKTEST'}
          </button>
        </div>
        {result && (
          <div className="self-end">
            <button onClick={runCalibrate} disabled={loading} className="px-6 py-2.5 rounded-md font-mono text-xs font-semibold tracking-wider transition-all cursor-pointer bg-surface2 text-text-muted border border-border/50">
              &#x2699; AUTO-CALIBRATE
            </button>
          </div>
        )}
      </div>

      {error && (
        <div className="px-5 py-3 bg-red-900/30 border border-red-500 rounded-md mb-5 text-[13px] text-red-400">
          {error}
        </div>
      )}

      {/* Summary Cards */}
      {result && (
        <>
          <div className="grid grid-cols-[repeat(auto-fit,minmax(160px,1fr))] gap-3 mb-6">
            <MetricCard label="Dates Tested" value={result.num_dates} color="text-blue-400" />
            <MetricCard label="Total Players" value={result.total_players?.toLocaleString()} color="text-purple-400" />
            <MetricCard label="Avg MAE" value={result.avg_mae} color={result.avg_mae < 4 ? 'text-venom' : 'text-venom'} subtitle="Lower is better" />
            <MetricCard label="Avg RMSE" value={result.avg_rmse} color={result.avg_rmse < 6 ? 'text-venom' : 'text-venom'} subtitle="Lower is better" />
            <MetricCard label="Correlation" value={result.avg_correlation} color={result.avg_correlation > 0.3 ? 'text-venom' : 'text-orange-400'} subtitle="Higher is better" />
            <MetricCard label="Within 20%" value={`${result.avg_hit_rate_20pct}%`} color="text-venom" />
            <MetricCard label="Top-10 Overlap" value={`${result.avg_top10_overlap}%`} color="text-blue-400" />
          </div>

          {/* Calibration Suggestions */}
          {result.calibration_suggestions && result.calibration_suggestions.length > 0 && (
            <div className="bg-surface rounded-lg p-5 border border-border mb-4 border-l-[3px] border-l-orange-400">
              <div className="text-xs text-venom tracking-widest uppercase mb-3 font-semibold">Calibration Suggestions</div>
              {result.calibration_suggestions.map((s, i) => (
                <div key={i} className="text-xs text-text-primary mb-2 pl-3">
                  &bull; {s}
                </div>
              ))}
            </div>
          )}

          {/* Auto-Calibration Results */}
          {result.calibration && (
            <div className="bg-surface rounded-lg p-5 border border-border mb-4 border-l-[3px] border-l-venom">
              <div className="text-xs text-venom tracking-widest uppercase mb-3 font-semibold">Auto-Calibration Adjustments</div>
              <div className="flex gap-4 flex-wrap">
                {Object.entries(result.calibration.adjustments || {}).map(([pos, mult]) => (
                  <div key={pos} className="text-center">
                    <div className="text-[10px] text-text-muted uppercase">{pos}</div>
                    <div className={`text-lg font-bold ${mult > 1.02 ? 'text-venom' : mult < 0.98 ? 'text-venom' : 'text-text-muted'}`}>
                      {mult}x
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <PositionTable byPosition={result.by_position} />
          <DateResults byDate={result.by_date} />
        </>
      )}

      {/* Empty State */}
      {!result && !loading && (
        <div className="bg-surface rounded-lg p-5 border border-border text-center py-[60px] px-10">
          <div className="text-5xl mb-4">&#x1F4CA;</div>
          <div className="text-base text-text-muted mb-2">
            Historical Backtesting
          </div>
          <div className="text-xs text-text-muted max-w-[400px] mx-auto leading-relaxed">
            Re-run simulations against past game results to measure projection accuracy.
            Select a date range and click Run Backtest to begin.
          </div>
        </div>
      )}
    </div>
  );
}
