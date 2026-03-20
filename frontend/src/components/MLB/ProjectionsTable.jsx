import React, { useState, useMemo } from 'react';

const POSITION_FILTERS = ['All', 'P', 'C', '1B', '2B', '3B', 'SS', 'OF'];
const PAGE_SIZE = 50;

export default function ProjectionsTable({ simResult, onPlayerClick, locks, excludes, onToggleLock, onToggleExclude }) {
  const [sortCol, setSortCol] = useState('dk_points');
  const [sortAsc, setSortAsc] = useState(false);
  const [posFilter, setPosFilter] = useState('All');
  const [teamFilter, setTeamFilter] = useState('All');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(0);

  const players = simResult?.players || [];

  const teams = useMemo(() => {
    const s = new Set(players.map(p => p.team));
    return ['All', ...Array.from(s).sort()];
  }, [players]);

  const filtered = useMemo(() => {
    let list = [...players];
    if (posFilter !== 'All') {
      if (posFilter === 'P') {
        list = list.filter(p => ['SP', 'RP', 'P'].includes(p.position));
      } else {
        list = list.filter(p => p.position === posFilter);
      }
    }
    if (teamFilter !== 'All') list = list.filter(p => p.team === teamFilter);
    if (search) {
      const q = search.toLowerCase();
      list = list.filter(p => p.name.toLowerCase().includes(q));
    }
    list.sort((a, b) => {
      const va = a[sortCol] ?? 0, vb = b[sortCol] ?? 0;
      return sortAsc ? (va > vb ? 1 : -1) : (va < vb ? 1 : -1);
    });
    return list;
  }, [players, posFilter, teamFilter, search, sortCol, sortAsc]);

  const pageCount = Math.ceil(filtered.length / PAGE_SIZE);
  const paged = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  const handleSort = (col) => {
    if (col === sortCol) setSortAsc(!sortAsc);
    else { setSortCol(col); setSortAsc(false); }
  };

  const SortIcon = ({ col }) => {
    if (col !== sortCol) return <span className="text-border">{' \u25B4\u25BE'}</span>;
    return <span className="text-venom">{sortAsc ? ' \u25B4' : ' \u25BE'}</span>;
  };

  if (!simResult) {
    return (
      <div className="py-20 text-center text-venom">
        Run a simulation to see player projections
      </div>
    );
  }

  return (
    <div>
      <h3 className="text-sm font-mono font-bold tracking-widest uppercase text-text-primary mb-4">
        PLAYER PROJECTIONS &mdash; {simResult.num_sims} SIMULATIONS
      </h3>

      {/* Filters */}
      <div className="flex gap-2.5 mb-4 flex-wrap items-center">
        <div className="flex gap-1">
          {POSITION_FILTERS.map(pos => (
            <button
              key={pos}
              onClick={() => { setPosFilter(pos); setPage(0); }}
              className={`px-3 py-1.5 rounded-md font-mono text-[11px] font-semibold tracking-wider transition-all cursor-pointer border ${
                posFilter === pos
                  ? 'bg-venom text-primary border-venom'
                  : 'bg-surface text-text-muted border-border/50 hover:border-venom/50'
              }`}
            >
              {pos}
            </button>
          ))}
        </div>
        <select
          value={teamFilter}
          onChange={e => { setTeamFilter(e.target.value); setPage(0); }}
          className="px-2.5 py-1.5 bg-surface border border-border/50 rounded-md text-text-primary font-mono text-[11px] outline-none"
        >
          {teams.map(t => <option key={t} value={t}>{t}</option>)}
        </select>
        <input
          placeholder="Search player..."
          value={search}
          onChange={e => { setSearch(e.target.value); setPage(0); }}
          className="px-2.5 py-1.5 bg-surface border border-border/50 rounded-md text-text-primary font-mono text-[11px] outline-none w-40"
        />
        <span className="text-text-muted text-[11px]">
          {filtered.length} players
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-xs">
          <thead>
            <tr>
              <th className="text-left px-3 py-2.5 border-b border-border/50 text-text-muted text-[10px] tracking-wider uppercase whitespace-nowrap">#</th>
              <th className="text-left px-3 py-2.5 border-b border-border/50 text-text-muted text-[10px] tracking-wider uppercase whitespace-nowrap">Actions</th>
              <th className="text-left px-3 py-2.5 border-b border-border/50 text-text-muted text-[10px] tracking-wider uppercase whitespace-nowrap cursor-pointer select-none" onClick={() => handleSort('name')}>
                Player<SortIcon col="name" />
              </th>
              <th className="text-left px-3 py-2.5 border-b border-border/50 text-text-muted text-[10px] tracking-wider uppercase whitespace-nowrap">Pos</th>
              <th className="text-left px-3 py-2.5 border-b border-border/50 text-text-muted text-[10px] tracking-wider uppercase whitespace-nowrap cursor-pointer select-none" onClick={() => handleSort('team')}>
                Team<SortIcon col="team" />
              </th>
              <th className="text-left px-3 py-2.5 border-b border-border/50 text-text-muted text-[10px] tracking-wider uppercase whitespace-nowrap">Opp</th>
              <th className="text-left px-3 py-2.5 border-b border-border/50 text-text-muted text-[10px] tracking-wider uppercase whitespace-nowrap cursor-pointer select-none" onClick={() => handleSort('salary')}>
                Salary<SortIcon col="salary" />
              </th>
              <th className="text-left px-3 py-2.5 border-b border-border/50 text-venom text-[10px] tracking-wider uppercase whitespace-nowrap cursor-pointer select-none" onClick={() => handleSort('dk_points')}>
                DK Pts<SortIcon col="dk_points" />
              </th>
              <th className="text-left px-3 py-2.5 border-b border-border/50 text-text-muted text-[10px] tracking-wider uppercase whitespace-nowrap cursor-pointer select-none" onClick={() => handleSort('floor')}>
                Floor<SortIcon col="floor" />
              </th>
              <th className="text-left px-3 py-2.5 border-b border-border/50 text-text-muted text-[10px] tracking-wider uppercase whitespace-nowrap cursor-pointer select-none" onClick={() => handleSort('ceiling')}>
                Ceil<SortIcon col="ceiling" />
              </th>
              <th className="text-left px-3 py-2.5 border-b border-border/50 text-text-muted text-[10px] tracking-wider uppercase whitespace-nowrap cursor-pointer select-none" onClick={() => handleSort('dk_std')}>
                Std<SortIcon col="dk_std" />
              </th>
              <th className="text-left px-3 py-2.5 border-b border-border/50 text-text-muted text-[10px] tracking-wider uppercase whitespace-nowrap cursor-pointer select-none" onClick={() => handleSort('value')}>
                Value<SortIcon col="value" />
              </th>
              <th className="text-left px-3 py-2.5 border-b border-border/50 text-text-muted text-[10px] tracking-wider uppercase whitespace-nowrap cursor-pointer select-none" onClick={() => handleSort('ownership_proj')}>
                Own%<SortIcon col="ownership_proj" />
              </th>
            </tr>
          </thead>
          <tbody>
            {paged.map((p, i) => {
              const globalIdx = page * PAGE_SIZE + i;
              const isLocked = locks?.includes(p.id);
              const isExcluded = excludes?.includes(p.id);
              return (
                <tr
                  key={p.id}
                  className={`${
                    isExcluded
                      ? 'bg-red-950/30 opacity-50'
                      : isLocked
                        ? 'bg-green-950/30'
                        : globalIdx % 2
                          ? 'bg-surface/50'
                          : 'bg-transparent'
                  } ${globalIdx < 3 ? 'border-l-[3px] border-l-venom' : ''}`}
                >
                  <td className="px-3 py-2 border-b border-border/30 whitespace-nowrap text-text-muted">{globalIdx + 1}</td>
                  <td className="px-3 py-2 border-b border-border/30 whitespace-nowrap">
                    <span
                      onClick={() => onToggleLock?.(p.id)}
                      title="Lock"
                      className={`cursor-pointer mr-1.5 ${isLocked ? 'opacity-100' : 'opacity-30'}`}
                    >
                      {isLocked ? '\uD83D\uDD12' : '\uD83D\uDD13'}
                    </span>
                    <span
                      onClick={() => onToggleExclude?.(p.id)}
                      title="Exclude"
                      className={`cursor-pointer ${isExcluded ? 'opacity-100' : 'opacity-30'}`}
                    >
                      {'\u274C'}
                    </span>
                  </td>
                  <td
                    className="px-3 py-2 border-b border-border/30 whitespace-nowrap font-semibold text-white cursor-pointer hover:text-venom transition-colors"
                    onClick={() => onPlayerClick?.(p)}
                  >
                    {p.name}
                  </td>
                  <td className="px-3 py-2 border-b border-border/30 whitespace-nowrap">
                    <span className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                      ['SP', 'RP', 'P'].includes(p.position)
                        ? 'bg-purple-900/40 text-purple-400'
                        : 'bg-blue-900/40 text-blue-400'
                    }`}>
                      {p.position}
                    </span>
                  </td>
                  <td className="px-3 py-2 border-b border-border/30 whitespace-nowrap text-text-primary">{p.team}</td>
                  <td className="px-3 py-2 border-b border-border/30 whitespace-nowrap text-text-primary">{p.is_home ? 'vs' : '@'} {p.opponent}</td>
                  <td className="px-3 py-2 border-b border-border/30 whitespace-nowrap text-text-primary">${p.salary?.toLocaleString() || '\u2014'}</td>
                  <td className="px-3 py-2 border-b border-border/30 whitespace-nowrap text-venom font-extrabold">
                    {p.dk_points?.toFixed(1)}
                  </td>
                  <td className="px-3 py-2 border-b border-border/30 whitespace-nowrap text-text-muted">{p.floor?.toFixed(1)}</td>
                  <td className="px-3 py-2 border-b border-border/30 whitespace-nowrap text-venom-glow">{p.ceiling?.toFixed(1)}</td>
                  <td className="px-3 py-2 border-b border-border/30 whitespace-nowrap text-text-muted">{p.dk_std?.toFixed(1)}</td>
                  <td className={`px-3 py-2 border-b border-border/30 whitespace-nowrap ${p.value > 5 ? 'text-venom' : 'text-text-muted'}`}>
                    {p.value > 0 ? p.value.toFixed(1) + 'x' : '\u2014'}
                  </td>
                  <td className="px-3 py-2 border-b border-border/30 whitespace-nowrap text-text-muted">
                    {p.ownership_proj ? p.ownership_proj.toFixed(1) + '%' : '\u2014'}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {pageCount > 1 && (
        <div className="flex gap-2 justify-center mt-4">
          <button
            onClick={() => setPage(Math.max(0, page - 1))}
            disabled={page === 0}
            className="px-4 py-1.5 rounded-md font-mono text-[11px] font-semibold tracking-wider transition-all cursor-pointer border border-border/50 bg-surface text-text-muted hover:border-venom/50 disabled:opacity-30 disabled:cursor-not-allowed"
          >
            &lt; Prev
          </button>
          <span className="text-text-muted text-xs leading-[30px]">
            Page {page + 1} / {pageCount}
          </span>
          <button
            onClick={() => setPage(Math.min(pageCount - 1, page + 1))}
            disabled={page >= pageCount - 1}
            className="px-4 py-1.5 rounded-md font-mono text-[11px] font-semibold tracking-wider transition-all cursor-pointer border border-border/50 bg-surface text-text-muted hover:border-venom/50 disabled:opacity-30 disabled:cursor-not-allowed"
          >
            Next &gt;
          </button>
        </div>
      )}
    </div>
  );
}
