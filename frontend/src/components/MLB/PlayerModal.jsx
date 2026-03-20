import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';

const API = 'http://localhost:5555/api';

export default function PlayerModal({ player, onClose }) {
  const [distData, setDistData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!player) return;
    setLoading(true);
    fetch(`${API}/player/${player.id}/distribution`)
      .then(r => r.json())
      .then(d => { setDistData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, [player]);

  if (!player) return null;

  const histogram = distData?.histogram;
  const chartData = histogram ? histogram.counts.map((count, i) => ({
    range: `${histogram.bin_edges[i].toFixed(1)}`,
    count,
    midpoint: (histogram.bin_edges[i] + histogram.bin_edges[i + 1]) / 2,
  })) : [];

  return (
    <div
      className="fixed inset-0 bg-black/85 z-[1000] flex items-center justify-center p-5"
      onClick={onClose}
    >
      <div
        className="bg-surface border border-border rounded-xl max-w-[720px] w-full max-h-[90vh] overflow-y-auto p-7"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex justify-between items-start mb-5">
          <div>
            <h2 className="text-white m-0 text-xl">{player.name}</h2>
            <div className="flex gap-2 mt-1.5">
              <span className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                ['SP', 'RP', 'P'].includes(player.position)
                  ? 'bg-purple-900/40 text-purple-400'
                  : 'bg-blue-900/40 text-blue-400'
              }`}>
                {player.position}
              </span>
              <span className="text-text-muted text-[13px]">{player.team}</span>
              <span className="text-text-muted text-[13px]">
                {player.is_home ? 'vs' : '@'} {player.opponent}
              </span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="bg-transparent text-text-muted border-none text-lg cursor-pointer px-2 py-1 hover:text-white transition-colors"
          >
            &times;
          </button>
        </div>

        {/* Key Stats Grid */}
        <div className="grid grid-cols-[repeat(auto-fit,minmax(100px,1fr))] gap-2.5 mb-6">
          {[
            { label: 'DK Pts', value: player.dk_points?.toFixed(1), colorClass: 'text-venom' },
            { label: 'Ceiling', value: distData?.max?.toFixed(1) || player.ceiling?.toFixed(1), colorClass: 'text-venom' },
            { label: 'Floor', value: distData?.min?.toFixed(1) || player.floor?.toFixed(1), colorClass: 'text-fangs' },
            { label: 'Median', value: distData?.median?.toFixed(1) || player.median?.toFixed(1), colorClass: 'text-blue-400' },
            { label: 'Std Dev', value: distData?.std?.toFixed(1) || player.dk_std?.toFixed(1), colorClass: 'text-text-muted' },
            { label: 'Salary', value: player.salary ? `$${player.salary.toLocaleString()}` : '\u2014', colorClass: 'text-white' },
            { label: 'Value', value: player.value > 0 ? `${player.value.toFixed(1)}x` : '\u2014', colorClass: player.value > 5 ? 'text-venom' : 'text-text-muted' },
            { label: 'Own%', value: player.ownership_proj ? `${player.ownership_proj.toFixed(1)}%` : '\u2014', colorClass: 'text-text-muted' },
          ].map(s => (
            <div key={s.label} className="bg-surface2 rounded-lg p-2.5 text-center">
              <div className="text-text-muted text-[10px] uppercase mb-1">{s.label}</div>
              <div className={`${s.colorClass} text-base font-bold`}>{s.value || '\u2014'}</div>
            </div>
          ))}
        </div>

        {/* Percentiles */}
        {distData && (
          <div className="mb-6">
            <h4 className="text-text-muted text-xs uppercase mb-2">
              Percentiles ({distData.num_sims} sims)
            </h4>
            <div className="flex gap-1.5 flex-wrap">
              {[
                { label: 'P10', value: distData.p10 },
                { label: 'P25', value: distData.p25 },
                { label: 'P50', value: distData.median },
                { label: 'P75', value: distData.p75 },
                { label: 'P90', value: distData.p90 },
                { label: 'P95', value: distData.p95 },
              ].map(p => (
                <div key={p.label} className="bg-primary border border-border/50 rounded-md px-3 py-1.5 text-center">
                  <div className="text-text-muted text-[9px]">{p.label}</div>
                  <div className="text-venom text-[13px] font-semibold">{p.value?.toFixed(1)}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Distribution Histogram */}
        <div className="mb-5">
          <h4 className="text-text-muted text-xs uppercase mb-2.5">
            Simulation Distribution
          </h4>
          {loading ? (
            <div className="h-[200px] flex items-center justify-center text-text-muted">
              Loading distribution...
            </div>
          ) : chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={chartData} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1a3d27" />
                <XAxis dataKey="range" tick={{ fill: '#6b9a7e', fontSize: 10 }} />
                <YAxis tick={{ fill: '#6b9a7e', fontSize: 10 }} />
                <Tooltip
                  contentStyle={{ background: '#0f2218', border: '1px solid #1a3d27', borderRadius: '6px' }}
                  labelStyle={{ color: '#6b9a7e' }}
                  itemStyle={{ color: '#00ff88' }}
                  formatter={(value) => [value, 'Frequency']}
                  labelFormatter={(label) => `DK Points: ${label}`}
                />
                <Bar dataKey="count" fill="#00ff88" radius={[2, 2, 0, 0]} />
                {distData && (
                  <ReferenceLine x={chartData.findIndex(d => d.midpoint >= distData.mean)?.toString()}
                    stroke="#00ff88" strokeDasharray="5 5" label={{ value: 'Mean', fill: '#00ff88', fontSize: 10 }} />
                )}
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[100px] flex items-center justify-center text-text-muted">
              No distribution data available
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
