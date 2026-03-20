import React from 'react';

function getHeatColor(value, min, max) {
  if (value == null) return 'bg-surface2/50';
  const ratio = Math.max(0, Math.min(1, (value - min) / (max - min || 1)));
  if (ratio > 0.7) return 'bg-[#661111]';
  if (ratio > 0.5) return 'bg-[#664411]';
  if (ratio > 0.3) return 'bg-[#335522]';
  return 'bg-[#113322]';
}

function getScoreBadge(score) {
  if (score == null) return { classes: 'bg-surface2/50 text-text-muted', label: '--' };
  if (score >= 8) return { classes: 'bg-[#441111] text-fangs', label: score.toFixed(1) };
  if (score >= 6) return { classes: 'bg-[#443311] text-[#ffaa44]', label: score.toFixed(1) };
  if (score >= 4) return { classes: 'bg-[#334411] text-[#aaff44]', label: score.toFixed(1) };
  return { classes: 'bg-[#113322] text-venom', label: score.toFixed(1) };
}

function getBarColor(barRatio) {
  if (barRatio > 0.7) return 'bg-venom';
  if (barRatio > 0.4) return 'bg-[#ffaa44]';
  return 'bg-venom';
}

export default function GameHeatmap({ games }) {
  if (!games || games.length === 0) {
    return (
      <div className="py-16 text-center text-text-muted">
        No game environment data available. Run a simulation first.
      </div>
    );
  }

  const impliedTotals = games.map(g => g.implied_total ?? g.over_under ?? 0).filter(Boolean);
  const minTotal = Math.min(...impliedTotals, 6);
  const maxTotal = Math.max(...impliedTotals, 12);

  return (
    <div>
      <h3 className="text-sm font-bold tracking-widest text-text-muted uppercase mb-4 font-mono">
        GAME ENVIRONMENT HEATMAP
      </h3>

      {/* Legend */}
      <div className="flex gap-5 mb-4 text-[10px] text-text-muted tracking-wider">
        <span>IMPLIED TOTAL:</span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-sm bg-[#113322] inline-block" /> LOW
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-sm bg-[#335522] inline-block" /> MED
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-sm bg-[#664411] inline-block" /> HIGH
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-sm bg-[#661111] inline-block" /> SMASH
        </span>
      </div>

      {/* Heatmap Grid */}
      <div className="grid grid-cols-[repeat(auto-fill,minmax(280px,1fr))] gap-2.5">
        {games.map((game, idx) => {
          const impliedTotal = game.implied_total ?? game.over_under ?? null;
          const parkFactor = game.park_factor ?? game.venue?.park_factor ?? null;
          const weatherImpact = game.weather_impact ?? game.weather?.impact ?? null;
          const envScore = computeEnvScore(impliedTotal, parkFactor, weatherImpact);
          const badge = getScoreBadge(envScore);
          const heatClass = getHeatColor(impliedTotal, minTotal, maxTotal);

          return (
            <div key={idx} className={`rounded-lg px-4 py-3.5 border border-border flex flex-col gap-2 ${heatClass}`}>
              {/* Matchup header */}
              <div className="flex justify-between items-center">
                <div className="text-sm font-bold text-text-primary">
                  {game.away_team?.abbr || game.away || '???'} @ {game.home_team?.abbr || game.home || '???'}
                </div>
                <div className={`inline-block px-2.5 py-0.5 rounded-full text-[11px] font-bold ${badge.classes}`}>
                  ENV {badge.label}
                </div>
              </div>

              {/* Pitchers */}
              <div className="text-[11px] text-text-muted">
                <span>{game.away_team?.probable_pitcher?.name || game.away_pitcher || 'TBD'}</span>
                <span className="text-text-muted/40 mx-1.5">vs</span>
                <span>{game.home_team?.probable_pitcher?.name || game.home_pitcher || 'TBD'}</span>
              </div>

              {/* Stat bars */}
              <div className="flex gap-2 mt-1">
                <StatCell label="TOTAL" value={impliedTotal} format={v => v.toFixed(1)} max={14} />
                <StatCell label="PARK" value={parkFactor} format={v => v.toFixed(2)} max={1.3} />
                <StatCell label="WTHR" value={weatherImpact} format={v => (v > 0 ? '+' : '') + v.toFixed(2)} max={0.3} isAbsolute />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function StatCell({ label, value, format, max, isAbsolute }) {
  const displayVal = value != null ? format(value) : '--';
  const barRatio = value != null
    ? Math.min(1, (isAbsolute ? Math.abs(value) : value) / max)
    : 0;
  const barColorClass = getBarColor(barRatio);

  return (
    <div className="flex-1">
      <div className="text-[9px] text-text-muted tracking-wider mb-0.5">
        {label}
      </div>
      <div className="text-[13px] font-semibold text-text-primary mb-0.5">
        {displayVal}
      </div>
      <div className="h-[3px] rounded-sm bg-border overflow-hidden">
        <div
          className={`h-full rounded-sm transition-[width] duration-300 ${barColorClass}`}
          style={{ width: `${barRatio * 100}%` }}
        />
      </div>
    </div>
  );
}

function computeEnvScore(impliedTotal, parkFactor, weatherImpact) {
  if (impliedTotal == null) return null;
  let score = 0;
  // Implied total contributes 0-5 points (based on range 6-14)
  score += Math.max(0, Math.min(5, ((impliedTotal - 6) / 8) * 5));
  // Park factor contributes 0-3 points (based on range 0.85-1.3)
  if (parkFactor != null) {
    score += Math.max(0, Math.min(3, ((parkFactor - 0.85) / 0.45) * 3));
  } else {
    score += 1.5; // neutral
  }
  // Weather impact contributes 0-2 points
  if (weatherImpact != null) {
    score += Math.max(0, Math.min(2, (weatherImpact + 0.1) / 0.3 * 2));
  } else {
    score += 1; // neutral
  }
  return score;
}
