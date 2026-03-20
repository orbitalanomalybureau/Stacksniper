import React, { useState } from 'react';

/**
 * AgentBreakdown -- Per-agent contribution breakdown for a player's projection.
 *
 * Props:
 *   playerName      - string
 *   agentOpinions   - array of { agent_name, agent_type, adjustment, confidence, reasoning }
 *   baseProjection  - number (base projection before agent adjustments)
 */

const AGENT_ICONS = {
  weather: '\u{1F324}\uFE0F',
  park: '\u{1F3DF}\uFE0F',
  vegas: '\u{1F4B0}',
  matchup: '\u26BE',
  momentum: '\u{1F525}',
  lineup_order: '\u{1F4CA}',
  bullpen: '\u{1F4AA}',
  umpire: '\u{2696}\uFE0F',
  rest_days: '\u{1F634}',
  handedness: '\u{1F91A}',
  implied_runs: '\u{1F4C8}',
  home_away: '\u{1F3E0}',
  recent_form: '\u{1F4C5}',
  correlation: '\u{1F517}',
  ml_projection: '\u{1F916}',
  pitcher: '\u26BE',
  batter: '\u26BE',
};

function getConfidenceLevel(confidence) {
  if (typeof confidence === 'string') return confidence.toLowerCase();
  if (typeof confidence === 'number') {
    if (confidence >= 0.7) return 'high';
    if (confidence >= 0.4) return 'medium';
    return 'low';
  }
  return 'medium';
}

function getConfidenceClasses(level) {
  switch (level) {
    case 'high':
      return { label: 'HIGH', bg: 'bg-venom/15', text: 'text-venom', border: 'border-venom/30' };
    case 'medium':
      return { label: 'MED', bg: 'bg-amber-500/15', text: 'text-amber-400', border: 'border-amber-500/30' };
    case 'low':
      return { label: 'LOW', bg: 'bg-red-500/15', text: 'text-red-400', border: 'border-red-500/30' };
    default:
      return { label: 'MED', bg: 'bg-amber-500/15', text: 'text-amber-400', border: 'border-amber-500/30' };
  }
}

function formatAgentName(name) {
  return name
    .replace(/_/g, ' ')
    .replace(/agent$/i, '')
    .trim()
    .replace(/\b\w/g, c => c.toUpperCase());
}

export default function AgentBreakdown({ playerName, agentOpinions = [], baseProjection = 0 }) {
  const [expanded, setExpanded] = useState(true);

  if (!agentOpinions || agentOpinions.length === 0) {
    return (
      <div className="bg-surface border border-border rounded-[10px] p-5 font-sans">
        <div className="text-xs text-venom tracking-[2px] uppercase font-semibold">Agent Breakdown</div>
        <div className="text-base text-white font-bold mt-1 mb-3">{playerName || 'Unknown'}</div>
        <div className="text-text-muted text-xs text-center py-5">
          No agent opinions available for this player.
        </div>
      </div>
    );
  }

  // Calculate totals
  const totalAdjustment = agentOpinions.reduce((sum, a) => sum + (a.adjustment || 0), 0);
  const finalProjection = baseProjection + totalAdjustment;
  const maxAbsAdj = Math.max(...agentOpinions.map(a => Math.abs(a.adjustment || 0)), 0.1);
  const positiveAdj = agentOpinions.filter(a => (a.adjustment || 0) > 0).reduce((s, a) => s + a.adjustment, 0);
  const negativeAdj = agentOpinions.filter(a => (a.adjustment || 0) < 0).reduce((s, a) => s + a.adjustment, 0);

  // Sort by absolute adjustment descending
  const sorted = [...agentOpinions].sort((a, b) => Math.abs(b.adjustment || 0) - Math.abs(a.adjustment || 0));

  return (
    <div className="bg-surface border border-border rounded-[10px] p-5 font-sans">
      {/* Header */}
      <div className="flex justify-between items-center mb-4">
        <div>
          <h4 className="text-xs text-venom tracking-[2px] uppercase font-semibold m-0">Agent Breakdown</h4>
          <div className="text-base text-white font-bold mt-1">{playerName || 'Unknown'}</div>
        </div>
        <div className="flex items-center gap-2.5">
          <button
            className="bg-transparent border border-border text-text-muted px-2.5 py-1 rounded text-[10px] cursor-pointer font-mono tracking-wider hover:border-venom/50 hover:text-text-primary transition-colors"
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? 'COLLAPSE' : 'EXPAND'}
          </button>
          <div className="bg-primary border border-border rounded-lg px-3.5 py-2 text-center">
            <div className="text-[9px] text-text-muted uppercase tracking-wider">Final</div>
            <div className="text-lg text-venom font-bold font-mono">
              {finalProjection.toFixed(1)}
            </div>
          </div>
        </div>
      </div>

      {/* Summary row */}
      <div className="flex gap-2.5 mb-4 flex-wrap">
        <div className="bg-primary rounded-md px-3.5 py-2 text-center flex-1 min-w-[80px]">
          <div className="text-[9px] text-text-muted uppercase tracking-wider">Base</div>
          <div className="text-[15px] font-bold font-mono mt-0.5 text-blue-400">{baseProjection.toFixed(1)}</div>
        </div>
        <div className="bg-primary rounded-md px-3.5 py-2 text-center flex-1 min-w-[80px]">
          <div className="text-[9px] text-text-muted uppercase tracking-wider">Boosts</div>
          <div className="text-[15px] font-bold font-mono mt-0.5 text-venom">
            +{positiveAdj.toFixed(1)}
          </div>
        </div>
        <div className="bg-primary rounded-md px-3.5 py-2 text-center flex-1 min-w-[80px]">
          <div className="text-[9px] text-text-muted uppercase tracking-wider">Fades</div>
          <div className="text-[15px] font-bold font-mono mt-0.5 text-fangs">
            {negativeAdj.toFixed(1)}
          </div>
        </div>
        <div className="bg-primary rounded-md px-3.5 py-2 text-center flex-1 min-w-[80px]">
          <div className="text-[9px] text-text-muted uppercase tracking-wider">Net Adj</div>
          <div className={`text-[15px] font-bold font-mono mt-0.5 ${totalAdjustment >= 0 ? 'text-venom' : 'text-fangs'}`}>
            {totalAdjustment >= 0 ? '+' : ''}{totalAdjustment.toFixed(1)}
          </div>
        </div>
        <div className="bg-primary rounded-md px-3.5 py-2 text-center flex-1 min-w-[80px]">
          <div className="text-[9px] text-text-muted uppercase tracking-wider">Agents</div>
          <div className="text-[15px] font-bold font-mono mt-0.5 text-white">{agentOpinions.length}</div>
        </div>
      </div>

      {/* Stacked bar visualization: base + each agent */}
      <div className="bg-primary rounded-md p-3 mb-4">
        <div className="text-[9px] text-text-muted uppercase tracking-wider mb-2">
          Projection Buildup
        </div>
        <div className="flex items-center h-7 rounded overflow-hidden">
          {(() => {
            const total = Math.max(finalProjection, baseProjection, 0.1);
            const basePct = (baseProjection / total) * 100;
            const segments = [
              { label: 'Base', width: Math.max(basePct, 5), color: 'bg-blue-900/40' },
            ];
            sorted.forEach(a => {
              const adj = a.adjustment || 0;
              const adjPct = Math.abs(adj / total) * 100;
              segments.push({
                label: a.agent_name,
                width: Math.max(adjPct, 1),
                color: adj >= 0 ? 'bg-venom/30' : 'bg-fangs/30',
              });
            });
            return segments.map((seg, idx) => (
              <div
                key={idx}
                title={seg.label}
                className={`h-full ${seg.color} border-r border-primary min-w-[2px] transition-all duration-300`}
                style={{ width: `${seg.width}%` }}
              />
            ));
          })()}
        </div>
        <div className="flex justify-between mt-1">
          <span className="text-[10px] text-blue-400">0</span>
          <span className="text-[10px] text-venom">{finalProjection.toFixed(1)} DKFP</span>
        </div>
      </div>

      {/* Agent rows */}
      {expanded && sorted.map((agent, idx) => {
        const adj = agent.adjustment || 0;
        const isPositive = adj >= 0;
        const barPct = (Math.abs(adj) / maxAbsAdj) * 100;
        const confLevel = getConfidenceLevel(agent.confidence);
        const conf = getConfidenceClasses(confLevel);
        const icon = AGENT_ICONS[agent.agent_type] || AGENT_ICONS[agent.agent_name] || '\u{1F50D}';
        const displayName = formatAgentName(agent.agent_name || agent.agent_type || 'Unknown');

        return (
          <div
            key={idx}
            className={`flex items-stretch gap-3 py-3 ${idx === sorted.length - 1 ? '' : 'border-b border-border/50'}`}
          >
            {/* Icon */}
            <div className="text-xl w-8 flex items-center justify-center shrink-0">{icon}</div>

            {/* Info */}
            <div className="flex-1 min-w-0">
              <div className="text-[13px] text-text-primary font-semibold mb-1 flex items-center gap-2">
                <span>{displayName}</span>
                <span className={`inline-block px-1.5 py-px rounded-lg text-[9px] font-bold font-mono tracking-wide border ${conf.bg} ${conf.text} ${conf.border}`}>
                  {conf.label}
                </span>
              </div>
              {agent.reasoning && (
                <div className="text-[11px] text-text-muted leading-[1.4] mt-1">{agent.reasoning}</div>
              )}
            </div>

            {/* Bar + value */}
            <div className="w-[180px] flex items-center gap-2 shrink-0">
              <div className="flex-1 h-5 bg-primary rounded relative overflow-hidden">
                {isPositive ? (
                  <div
                    className="absolute left-1/2 top-0 h-full bg-venom/35 rounded-r transition-all duration-400"
                    style={{ width: `${barPct / 2}%` }}
                  />
                ) : (
                  <div
                    className="absolute right-1/2 top-0 h-full bg-fangs/35 rounded-l transition-all duration-400"
                    style={{ width: `${barPct / 2}%` }}
                  />
                )}
                {/* Center line */}
                <div className="absolute left-1/2 top-0 w-px h-full bg-border" />
              </div>
              <div className={`text-[13px] font-bold font-mono w-[55px] text-right shrink-0 ${isPositive ? 'text-venom' : 'text-fangs'}`}>
                {isPositive ? '+' : ''}{adj.toFixed(1)}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
