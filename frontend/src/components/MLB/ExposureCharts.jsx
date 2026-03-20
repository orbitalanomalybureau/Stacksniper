import React, { useMemo, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

const POSITION_FILTERS = ['All', 'P', 'C', '1B', '2B', '3B', 'SS', 'OF'];

function getExposureColor(pct) {
  if (pct > 60) return '#00ff88';
  if (pct > 30) return '#ffaa44';
  return '#2ecc71';
}

export default function ExposureCharts({ lineups }) {
  const [posFilter, setPosFilter] = useState('All');
  const [sortBy, setSortBy] = useState('exposure');

  const exposureData = useMemo(() => {
    if (!lineups || lineups.length === 0) return [];

    const counts = {};
    const playerInfo = {};

    lineups.forEach(lu => {
      (lu.players || []).forEach(p => {
        const key = p.name || p.id;
        if (!counts[key]) {
          counts[key] = 0;
          playerInfo[key] = { name: p.name, team: p.team, position: p.position, salary: p.salary };
        }
        counts[key]++;
      });
    });

    const total = lineups.length;
    return Object.entries(counts).map(([name, count]) => ({
      name: playerInfo[name]?.name || name,
      team: playerInfo[name]?.team || '',
      position: playerInfo[name]?.position || '',
      salary: playerInfo[name]?.salary || 0,
      exposure: parseFloat(((count / total) * 100).toFixed(1)),
      count,
    }));
  }, [lineups]);

  const filtered = useMemo(() => {
    let data = [...exposureData];
    if (posFilter !== 'All') {
      if (posFilter === 'P') {
        data = data.filter(d => ['SP', 'RP', 'P'].includes(d.position));
      } else {
        data = data.filter(d => d.position === posFilter);
      }
    }
    data.sort((a, b) => {
      if (sortBy === 'exposure') return b.exposure - a.exposure;
      if (sortBy === 'name') return a.name.localeCompare(b.name);
      if (sortBy === 'salary') return b.salary - a.salary;
      return 0;
    });
    return data.slice(0, 30);
  }, [exposureData, posFilter, sortBy]);

  if (!lineups || lineups.length === 0) {
    return (
      <div className="py-10 text-center text-text-muted">
        Generate lineups to see exposure analysis
      </div>
    );
  }

  const CustomTooltip = ({ active, payload }) => {
    if (!active || !payload?.length) return null;
    const d = payload[0].payload;
    return (
      <div className="bg-surface border border-border/50 rounded-md px-3.5 py-2.5 text-[11px]">
        <div className="font-bold text-text-primary mb-1">{d.name}</div>
        <div className="text-text-muted">{d.team} / {d.position}</div>
        <div className="font-semibold mt-1" style={{ color: getExposureColor(d.exposure) }}>
          {d.exposure}% ({d.count}/{lineups.length} lineups)
        </div>
        {d.salary > 0 && (
          <div className="text-text-muted">${d.salary.toLocaleString()}</div>
        )}
      </div>
    );
  };

  return (
    <div className="bg-surface rounded-lg p-5 border border-border mt-5">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-text-primary text-sm font-bold tracking-wider uppercase">
          PLAYER EXPOSURE
        </h3>
        <div className="flex gap-2 items-center">
          <div className="flex gap-1">
            {POSITION_FILTERS.map(pos => (
              <button
                key={pos}
                onClick={() => setPosFilter(pos)}
                className={`px-2.5 py-1 rounded-md font-mono text-[10px] font-semibold tracking-wider border transition-colors ${
                  posFilter === pos
                    ? 'bg-venom text-primary border-venom'
                    : 'bg-surface2 text-text-muted border-border/50 hover:border-venom/50 hover:text-text-primary'
                }`}
              >
                {pos}
              </button>
            ))}
          </div>
          <select
            value={sortBy}
            onChange={e => setSortBy(e.target.value)}
            className="bg-surface2 border border-border/50 rounded-md px-2 py-1 text-[10px] text-text-muted focus:outline-none focus:border-venom"
          >
            <option value="exposure">Sort: Exposure</option>
            <option value="salary">Sort: Salary</option>
            <option value="name">Sort: Name</option>
          </select>
        </div>
      </div>

      {/* Exposure legend */}
      <div className="flex gap-4 mb-3 text-[10px] text-text-muted tracking-wider">
        <span className="flex items-center gap-1">
          <span className="w-2.5 h-2.5 rounded-sm bg-venom-glow inline-block" /> UNDER 30%
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2.5 h-2.5 rounded-sm inline-block" style={{ background: '#ffaa44' }} /> 30-60%
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2.5 h-2.5 rounded-sm bg-venom inline-block" /> OVER 60%
        </span>
      </div>

      {/* Chart */}
      <div className="w-full" style={{ height: Math.max(300, filtered.length * 28) }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={filtered} layout="vertical" margin={{ top: 0, right: 20, bottom: 0, left: 100 }}>
            <XAxis
              type="number"
              domain={[0, 100]}
              tick={{ fill: '#6b9a7e', fontSize: 10 }}
              tickFormatter={v => `${v}%`}
              axisLine={{ stroke: '#1a3d27' }}
              tickLine={false}
            />
            <YAxis
              type="category"
              dataKey="name"
              tick={{ fill: '#6b9a7e', fontSize: 10 }}
              axisLine={false}
              tickLine={false}
              width={95}
            />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
            <Bar dataKey="exposure" radius={[0, 4, 4, 0]} maxBarSize={20}>
              {filtered.map((entry, index) => (
                <Cell key={index} fill={getExposureColor(entry.exposure)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
