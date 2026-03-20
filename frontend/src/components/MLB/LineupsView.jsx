import React, { useState } from 'react';

export default function LineupsView({ lineups, onExportCSV }) {
  const [expandedIdx, setExpandedIdx] = useState(null);

  if (!lineups || lineups.length === 0) {
    return (
      <div className="py-20 text-center text-venom">
        Generate lineups to see optimized rosters
      </div>
    );
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-text-muted text-[10px] font-semibold tracking-[2px] uppercase">
          OPTIMIZED LINEUPS &mdash; {lineups.length} GENERATED
        </h3>
        {onExportCSV && (
          <button
            onClick={onExportCSV}
            className="px-4 py-1.5 rounded-md font-mono text-[10px] font-semibold tracking-wider border border-border bg-surface text-text-muted hover:text-text-primary hover:border-venom transition-colors"
          >
            Export DK CSV
          </button>
        )}
      </div>

      <div className="grid gap-3">
        {lineups.map((lu, idx) => (
          <div
            key={idx}
            className={`bg-surface rounded-lg p-5 cursor-pointer transition-colors ${
              expandedIdx === idx
                ? 'border border-venom'
                : 'border border-border'
            }`}
            onClick={() => setExpandedIdx(expandedIdx === idx ? null : idx)}
          >
            {/* Lineup Header */}
            <div className="flex justify-between items-center">
              <div className="flex items-center gap-3">
                <span
                  className={`rounded-full w-7 h-7 flex items-center justify-center text-xs font-bold ${
                    idx < 3
                      ? 'bg-venom text-primary'
                      : 'bg-surface2 text-text-muted'
                  }`}
                >
                  {lu.rank || idx + 1}
                </span>
                <div>
                  <span className="text-venom font-bold text-base">
                    {lu.projected?.toFixed(1)} pts
                  </span>
                  <span className="text-text-muted text-[11px] ml-2.5">
                    ${lu.salary?.toLocaleString()} / $50,000
                  </span>
                </div>
              </div>
              <div className="flex gap-4 items-center">
                <div className="text-right">
                  <div className="text-venom text-[11px]">
                    Ceil: {lu.ceiling?.toFixed(1)}
                  </div>
                  <div className="text-text-muted text-[11px]">
                    Floor: {lu.floor?.toFixed(1)}
                  </div>
                </div>
                <span className="text-text-muted text-[11px]">
                  ${lu.salary_remaining?.toLocaleString()} rem
                </span>
                <span
                  className={`text-text-muted transition-transform duration-200 ${
                    expandedIdx === idx ? 'rotate-180' : ''
                  }`}
                >
                  &#9660;
                </span>
              </div>
            </div>

            {/* Expanded Player List */}
            {expandedIdx === idx && (
              <div className="mt-3.5 border-t border-border/30 pt-3">
                <table className="w-full border-collapse text-xs">
                  <thead>
                    <tr>
                      <th className="text-left px-2 py-1.5 border-b border-border/50 text-text-muted text-[10px] tracking-wider uppercase whitespace-nowrap">
                        Pos
                      </th>
                      <th className="text-left px-2 py-1.5 border-b border-border/50 text-text-muted text-[10px] tracking-wider uppercase whitespace-nowrap">
                        Player
                      </th>
                      <th className="text-left px-2 py-1.5 border-b border-border/50 text-text-muted text-[10px] tracking-wider uppercase whitespace-nowrap">
                        Team
                      </th>
                      <th className="text-left px-2 py-1.5 border-b border-border/50 text-text-muted text-[10px] tracking-wider uppercase whitespace-nowrap">
                        Salary
                      </th>
                      <th className="text-left px-2 py-1.5 border-b border-border/50 text-text-muted text-[10px] tracking-wider uppercase whitespace-nowrap">
                        DK Pts
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {lu.players?.map((p, pi) => (
                      <tr
                        key={pi}
                        className={pi % 2 ? 'bg-surface2' : 'bg-transparent'}
                      >
                        <td className="px-2 py-1.5 border-b border-border/30 whitespace-nowrap">
                          <span
                            className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                              ['SP', 'RP', 'P'].includes(p.position)
                                ? 'bg-purple-900/30 text-purple-400'
                                : 'bg-blue-900/30 text-blue-400'
                            }`}
                          >
                            {p.position}
                          </span>
                        </td>
                        <td className="px-2 py-1.5 border-b border-border/30 whitespace-nowrap font-semibold text-text-primary text-left">
                          {p.name}
                        </td>
                        <td className="px-2 py-1.5 border-b border-border/30 whitespace-nowrap">
                          {p.team}
                        </td>
                        <td className="px-2 py-1.5 border-b border-border/30 whitespace-nowrap">
                          ${p.salary?.toLocaleString()}
                        </td>
                        <td className="px-2 py-1.5 border-b border-border/30 whitespace-nowrap text-venom font-bold">
                          {p.dk_points?.toFixed(1)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
