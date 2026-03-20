import React, { useState, useEffect, useMemo } from 'react';

const POSITIONS_HITTER = ['C', '1B', '2B', '3B', 'SS', 'OF', 'DH', 'LF', 'CF', 'RF'];
const POSITIONS_PITCHER = ['SP', 'RP', 'P'];
const CONFIDENCE_LEVELS = ['high', 'medium', 'low'];

function edgeColorClass(overPct) {
  if (overPct >= 65 || overPct <= 35) return 'text-venom';
  if (overPct >= 55 || overPct <= 45) return 'text-amber-400';
  return 'text-text-muted';
}

function edgeBarColor(overPct) {
  if (overPct >= 65 || overPct <= 35) return 'bg-venom';
  if (overPct >= 55 || overPct <= 45) return 'bg-amber-400';
  return 'bg-text-muted';
}

function OverUnderBar({ overPct, underPct }) {
  const overCls = edgeColorClass(overPct);
  const underCls = edgeColorClass(underPct);
  const overBar = edgeBarColor(overPct);
  const underBar = edgeBarColor(underPct);

  return (
    <div className="flex items-center gap-1.5 text-xs">
      <span className={`${overCls} font-semibold min-w-[48px] text-right`}>
        {overPct}%
      </span>
      <div className="flex-1 h-1.5 rounded-full bg-surface2 overflow-hidden flex min-w-[80px]">
        <div
          className={`${overBar} rounded-l-full transition-all duration-300`}
          style={{ width: `${overPct}%` }}
        />
        <div
          className={`${underBar} rounded-r-full transition-all duration-300`}
          style={{ width: `${underPct}%` }}
        />
      </div>
      <span className={`${underCls} font-semibold min-w-[48px]`}>
        {underPct}%
      </span>
    </div>
  );
}

function PlayerPropsRow({ playerData, expanded, onToggle }) {
  const topEdge = playerData.props.reduce(
    (best, p) => (p.edge > best.edge ? p : best), { edge: 0 }
  );

  return (
    <div className="bg-surface rounded-lg mb-2 border border-border overflow-hidden">
      {/* Header row */}
      <div
        onClick={onToggle}
        className={`flex items-center px-4 py-3 cursor-pointer gap-4 ${
          expanded ? 'border-b border-border' : ''
        }`}
      >
        <span className="text-base w-5 text-center text-text-muted">
          {expanded ? '\u25BC' : '\u25B6'}
        </span>
        <span className="font-bold text-[13px] text-text-primary min-w-[160px]">
          {playerData.player_name}
        </span>
        <span className="text-[10px] tracking-wider text-text-muted bg-surface2 px-2 py-0.5 rounded">
          {playerData.position}
        </span>
        <span className="text-[10px] tracking-wider text-text-muted bg-surface2 px-2 py-0.5 rounded">
          {playerData.team}
        </span>
        <div className="flex-1" />
        {topEdge.edge > 0 && (
          <span className={`text-[10px] px-2.5 py-0.5 rounded-full font-bold tracking-wider uppercase ${
            topEdge.confidence === 'high'
              ? 'bg-venom/15 text-venom'
              : topEdge.confidence === 'medium'
              ? 'bg-amber-400/15 text-amber-400'
              : 'bg-surface2 text-text-muted'
          }`}>
            {topEdge.confidence} edge
          </span>
        )}
        <span className="text-[11px] text-text-muted">
          {playerData.props.length} props
        </span>
      </div>

      {/* Expanded prop lines */}
      {expanded && (
        <div className="px-4 py-2 pb-3">
          <table className="w-full border-collapse text-xs">
            <thead>
              <tr>
                {['Prop', 'Line', 'Over / Under', 'Edge', 'Confidence', 'Mean', 'Median'].map(h => (
                  <th key={h} className="text-left px-2.5 py-1.5 border-b border-border/50 text-text-muted text-[10px] tracking-wider uppercase">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {playerData.props.map((prop, idx) => (
                <tr key={`${prop.prop}-${prop.line}-${idx}`} className="border-b border-border/30">
                  <td className="px-2.5 py-2 font-semibold capitalize">
                    {prop.prop.replace(/_/g, ' ')}
                  </td>
                  <td className="px-2.5 py-2 text-blue-400 font-bold">
                    {prop.line}
                  </td>
                  <td className="px-2.5 py-2 min-w-[220px]">
                    <OverUnderBar overPct={prop.over_pct} underPct={prop.under_pct} />
                  </td>
                  <td className={`px-2.5 py-2 font-bold ${
                    prop.confidence === 'high' ? 'text-venom'
                    : prop.confidence === 'medium' ? 'text-amber-400'
                    : 'text-text-muted'
                  }`}>
                    {prop.edge}%
                  </td>
                  <td className="px-2.5 py-2">
                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold tracking-wider uppercase ${
                      prop.confidence === 'high'
                        ? 'bg-venom/15 text-venom'
                        : prop.confidence === 'medium'
                        ? 'bg-amber-400/15 text-amber-400'
                        : 'bg-surface2 text-text-muted'
                    }`}>
                      {prop.confidence}
                    </span>
                  </td>
                  <td className="px-2.5 py-2 text-text-muted">
                    {prop.mean}
                  </td>
                  <td className="px-2.5 py-2 text-text-muted">
                    {prop.median}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default function PropsView({ simId }) {
  const [propsData, setPropsData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [expandedPlayers, setExpandedPlayers] = useState({});
  const [search, setSearch] = useState('');
  const [posFilter, setPosFilter] = useState('all');
  const [teamFilter, setTeamFilter] = useState('all');
  const [confidenceFilter, setConfidenceFilter] = useState('all');
  const [propTypeFilter, setPropTypeFilter] = useState('all');
  const [sortBy, setSortBy] = useState('edge');
  const [section, setSection] = useState('hitters');

  useEffect(() => {
    if (!simId) return;
    setLoading(true);
    setError(null);
    fetch(`/api/props?sim_id=${simId}`)
      .then(r => r.json())
      .then(data => {
        if (data.error) throw new Error(data.error);
        setPropsData(data.props || data);
        setLoading(false);
      })
      .catch(e => {
        setError(e.message);
        setLoading(false);
      });
  }, [simId]);

  const toggleExpand = (playerId) => {
    setExpandedPlayers(prev => ({ ...prev, [playerId]: !prev[playerId] }));
  };

  const teams = useMemo(() => {
    if (!propsData) return [];
    const t = [...new Set(propsData.map(p => p.team))].sort();
    return t;
  }, [propsData]);

  const propTypes = useMemo(() => {
    if (!propsData) return [];
    const types = new Set();
    propsData.forEach(p => p.props.forEach(pr => types.add(pr.prop)));
    return [...types].sort();
  }, [propsData]);

  const filteredData = useMemo(() => {
    if (!propsData) return { hitters: [], pitchers: [] };

    let data = propsData.map(player => {
      let filteredProps = player.props;

      if (confidenceFilter !== 'all') {
        filteredProps = filteredProps.filter(p => p.confidence === confidenceFilter);
      }
      if (propTypeFilter !== 'all') {
        filteredProps = filteredProps.filter(p => p.prop === propTypeFilter);
      }

      return { ...player, props: filteredProps };
    }).filter(p => p.props.length > 0);

    if (search) {
      const q = search.toLowerCase();
      data = data.filter(p => p.player_name.toLowerCase().includes(q));
    }
    if (teamFilter !== 'all') {
      data = data.filter(p => p.team === teamFilter);
    }
    if (posFilter !== 'all') {
      data = data.filter(p => p.position === posFilter);
    }

    // Sort
    if (sortBy === 'edge') {
      data.sort((a, b) => {
        const aMax = Math.max(...a.props.map(p => p.edge));
        const bMax = Math.max(...b.props.map(p => p.edge));
        return bMax - aMax;
      });
    } else if (sortBy === 'name') {
      data.sort((a, b) => a.player_name.localeCompare(b.player_name));
    } else if (sortBy === 'prop') {
      data.sort((a, b) => {
        const aProp = a.props[0]?.prop || '';
        const bProp = b.props[0]?.prop || '';
        return aProp.localeCompare(bProp);
      });
    }

    const hitters = data.filter(p => !POSITIONS_PITCHER.includes(p.position));
    const pitchers = data.filter(p => POSITIONS_PITCHER.includes(p.position));

    return { hitters, pitchers };
  }, [propsData, search, posFilter, teamFilter, confidenceFilter, propTypeFilter, sortBy]);

  if (!simId) {
    return (
      <div className="text-center py-16 px-5 text-text-muted">
        <div className="text-5xl mb-4 opacity-30">&#x1F3AF;</div>
        <div className="text-sm mb-2">No Simulation Data</div>
        <div className="text-xs text-text-muted">
          Run a simulation first to see props analysis
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="text-center py-16 px-5 text-text-muted">
        <div className="text-sm">Analyzing props...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="px-5 py-4 bg-red-900/30 border border-red-500 rounded-md text-red-400 text-[13px]">
        Props analysis error: {error}
      </div>
    );
  }

  const currentData = section === 'hitters' ? filteredData.hitters : filteredData.pitchers;
  const posOptions = section === 'hitters' ? POSITIONS_HITTER : POSITIONS_PITCHER;

  return (
    <div>
      {/* Section toggle */}
      <div className="flex mb-5">
        {['hitters', 'pitchers'].map(s => (
          <div
            key={s}
            onClick={() => { setSection(s); setPosFilter('all'); }}
            className={`px-7 py-2.5 cursor-pointer text-xs font-bold tracking-wider uppercase transition-all ${
              section === s
                ? 'bg-surface text-venom border-b-2 border-venom'
                : 'bg-transparent text-text-muted border-b-2 border-transparent hover:text-text-primary'
            }`}
          >
            {s === 'hitters' ? 'Hitter Props' : 'Pitcher Props'}
            <span className="ml-2 text-[10px] opacity-60">
              ({s === 'hitters' ? filteredData.hitters.length : filteredData.pitchers.length})
            </span>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="flex gap-3 mb-4 flex-wrap items-center">
        <input
          type="text"
          placeholder="Search player..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="px-3.5 py-2 bg-surface2 border border-border/50 rounded-md text-text-primary text-[11px] outline-none min-w-[180px] cursor-text focus:border-venom/50 transition-colors"
        />
        <select value={posFilter} onChange={e => setPosFilter(e.target.value)} className="px-3 py-1.5 bg-surface2 border border-border/50 rounded-md text-text-primary text-[11px] outline-none cursor-pointer">
          <option value="all">All Positions</option>
          {posOptions.map(p => <option key={p} value={p}>{p}</option>)}
        </select>
        <select value={teamFilter} onChange={e => setTeamFilter(e.target.value)} className="px-3 py-1.5 bg-surface2 border border-border/50 rounded-md text-text-primary text-[11px] outline-none cursor-pointer">
          <option value="all">All Teams</option>
          {teams.map(t => <option key={t} value={t}>{t}</option>)}
        </select>
        <select value={confidenceFilter} onChange={e => setConfidenceFilter(e.target.value)} className="px-3 py-1.5 bg-surface2 border border-border/50 rounded-md text-text-primary text-[11px] outline-none cursor-pointer">
          <option value="all">All Confidence</option>
          {CONFIDENCE_LEVELS.map(c => <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>)}
        </select>
        <select value={propTypeFilter} onChange={e => setPropTypeFilter(e.target.value)} className="px-3 py-1.5 bg-surface2 border border-border/50 rounded-md text-text-primary text-[11px] outline-none cursor-pointer">
          <option value="all">All Prop Types</option>
          {propTypes.map(p => (
            <option key={p} value={p}>{p.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</option>
          ))}
        </select>
        <div className="flex-1" />
        <span className="text-[10px] text-text-muted tracking-wider">SORT BY:</span>
        {['edge', 'name', 'prop'].map(s => (
          <span
            key={s}
            onClick={() => setSortBy(s)}
            className={`text-[10px] cursor-pointer tracking-wider uppercase px-2.5 py-1 rounded ${
              sortBy === s
                ? 'bg-venom/15 text-venom font-bold'
                : 'text-text-muted hover:text-text-primary'
            }`}
          >
            {s}
          </span>
        ))}
      </div>

      {/* Player list */}
      {currentData.length === 0 ? (
        <div className="text-center py-10 text-text-muted text-[13px]">
          No props data available for current filters
        </div>
      ) : (
        currentData.map(player => (
          <PlayerPropsRow
            key={player.player_id}
            playerData={player}
            expanded={!!expandedPlayers[player.player_id]}
            onToggle={() => toggleExpand(player.player_id)}
          />
        ))
      )}
    </div>
  );
}
