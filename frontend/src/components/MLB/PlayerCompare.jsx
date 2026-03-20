import React from 'react';

const STATS = [
  { key: 'dk_points', label: 'Projection', format: v => v?.toFixed(1) ?? '--' },
  { key: 'ceiling', label: 'Ceiling', format: v => v?.toFixed(1) ?? '--' },
  { key: 'floor', label: 'Floor', format: v => v?.toFixed(1) ?? '--' },
  { key: 'salary', label: 'Salary', format: v => v ? `$${v.toLocaleString()}` : '--' },
  { key: 'value', label: 'Value', format: v => v ? `${v.toFixed(1)}x` : '--' },
  { key: 'ownership_proj', label: 'Own%', format: v => v ? `${v.toFixed(1)}%` : '--' },
];

const PLAYER_COLORS = ['text-venom', 'text-blue-400', 'text-venom', 'text-purple-400'];
const PLAYER_BG_COLORS = ['bg-venom', 'bg-blue-400', 'bg-venom', 'bg-purple-400'];
const PLAYER_BORDER_COLORS = ['border-t-venom', 'border-t-blue-400', 'border-t-venom', 'border-t-purple-400'];
const PLAYER_RAW_COLORS = ['#00ff88', '#60a5fa', '#00ff88', '#a855f6'];

function getStatMax(players, key) {
  const vals = players.map(p => p[key] ?? 0).filter(Boolean);
  return Math.max(...vals, 1);
}

export default function PlayerCompare({ players, onRemovePlayer }) {
  if (!players || players.length === 0) {
    return (
      <div className="bg-surface rounded-lg p-10 border border-border text-center text-text-muted">
        Click players in the projections table to compare (2-4 players)
      </div>
    );
  }

  return (
    <div className="bg-surface rounded-lg p-5 border border-border mt-5">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-venom text-xs font-semibold tracking-widest uppercase m-0">PLAYER COMPARISON</h3>
        {players.length > 0 && (
          <span className="text-[10px] text-text-muted">
            {players.length}/4 PLAYERS
          </span>
        )}
      </div>

      {/* Player headers */}
      <div
        className="grid gap-2 mb-4"
        style={{ gridTemplateColumns: `120px repeat(${players.length}, 1fr)` }}
      >
        <div /> {/* spacer for label column */}
        {players.map((p, i) => (
          <div
            key={p.id || i}
            className={`bg-surface2 rounded-lg p-3 text-center border-t-[3px] ${PLAYER_BORDER_COLORS[i]} relative`}
          >
            {onRemovePlayer && (
              <span
                onClick={() => onRemovePlayer(p.id || i)}
                className="absolute top-1 right-2 cursor-pointer text-text-muted text-sm leading-none hover:text-white"
              >
                &times;
              </span>
            )}
            <div className="font-bold text-white text-[13px]">
              {p.name}
            </div>
            <div className="text-[10px] text-text-muted mt-0.5">
              {p.team} / {p.position}
            </div>
          </div>
        ))}
      </div>

      {/* Stat rows */}
      {STATS.map(stat => {
        const max = getStatMax(players, stat.key);
        return (
          <div
            key={stat.key}
            className="grid gap-2 mb-2.5 items-center"
            style={{ gridTemplateColumns: `120px repeat(${players.length}, 1fr)` }}
          >
            <div className="text-[10px] text-text-muted tracking-wider uppercase">
              {stat.label}
            </div>
            {players.map((p, i) => {
              const val = p[stat.key] ?? 0;
              const barPct = stat.key === 'salary'
                ? Math.min(100, (val / 15000) * 100)
                : Math.min(100, (val / max) * 100);
              const isBest = val === Math.max(...players.map(pl => pl[stat.key] ?? 0));

              return (
                <div key={p.id || i} className="bg-surface2 rounded-md px-3 py-2">
                  <div className={`text-sm font-bold mb-1 ${isBest ? PLAYER_COLORS[i] : 'text-text-primary'}`}>
                    {stat.format(p[stat.key])}
                    {isBest && players.length > 1 && (
                      <span className={`text-[8px] ${PLAYER_COLORS[i]} ml-1.5 tracking-wider`}>BEST</span>
                    )}
                  </div>
                  <div className="h-1 rounded-sm bg-border overflow-hidden">
                    <div
                      className={`h-full rounded-sm ${PLAYER_BG_COLORS[i]} opacity-70 transition-all duration-300`}
                      style={{ width: `${barPct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        );
      })}
    </div>
  );
}
