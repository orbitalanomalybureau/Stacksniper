import React, { useState, useEffect, useRef } from 'react';

export default function LiveView({ lineups, simResult }) {
  const [scores, setScores] = useState(null);
  const [tracking, setTracking] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(null);
  const intervalRef = useRef(null);

  const startTracking = async () => {
    try {
      const res = await fetch('/api/live/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      setTracking(true);
      fetchScores();
      intervalRef.current = setInterval(fetchScores, 30000);
    } catch (e) {
      console.error('Failed to start tracking:', e);
    }
  };

  const stopTracking = () => {
    setTracking(false);
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  };

  useEffect(() => {
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);

  const fetchScores = async () => {
    try {
      const res = await fetch('/api/live/scores');
      const data = await res.json();
      setScores(data);
      setLastUpdate(new Date());
    } catch (e) {
      console.error('Failed to fetch scores:', e);
    }
  };

  const getPlayerScore = (playerId) => {
    return scores?.players?.[String(playerId)] || null;
  };

  const getScoreColor = (current, projected) => {
    if (!projected || projected === 0) return 'text-text-primary';
    const ratio = current / projected;
    if (ratio >= 1.0) return 'text-venom';
    if (ratio >= 0.7) return 'text-yellow-400';
    return 'text-red-400';
  };

  const getScoreBorderColor = (current, projected) => {
    if (!projected || projected === 0) return 'border-text-primary';
    const ratio = current / projected;
    if (ratio >= 1.0) return 'border-venom';
    if (ratio >= 0.7) return 'border-yellow-400';
    return 'border-red-400';
  };

  return (
    <div className="py-5">
      {/* Header */}
      <div className="flex justify-between items-center mb-5">
        <div>
          <h3 className="text-venom m-0 text-base font-bold">
            ⚡ Live Scoring
          </h3>
          {lastUpdate && (
            <div className="text-text-muted text-[10px] mt-1">
              Last updated: {lastUpdate.toLocaleTimeString()}
            </div>
          )}
        </div>
        <div className="flex gap-2.5">
          {!tracking ? (
            <button onClick={startTracking} className="px-4 py-2 rounded-md border-none bg-venom text-black font-bold text-xs cursor-pointer font-inherit">
              Start Tracking
            </button>
          ) : (
            <>
              <button onClick={fetchScores} className="px-4 py-2 rounded-md border border-border bg-transparent text-text-primary text-xs cursor-pointer font-inherit">
                ↻ Refresh
              </button>
              <button onClick={stopTracking} className="px-4 py-2 rounded-md border border-red-400 bg-transparent text-red-400 text-xs cursor-pointer font-inherit">
                Stop
              </button>
            </>
          )}
        </div>
      </div>

      {!tracking && !scores && (
        <div className="text-center py-[60px] px-5 text-text-muted text-[13px]">
          Click "Start Tracking" to begin live score updates.<br />
          <span className="text-[11px]">Scores refresh every 30 seconds.</span>
        </div>
      )}

      {/* Lineup Cards */}
      {lineups && lineups.length > 0 && scores && (
        <div className="grid gap-4">
          {lineups.slice(0, 10).map((lineup, idx) => {
            const players = lineup.players || [];
            const currentTotal = players.reduce((sum, p) => {
              const live = getPlayerScore(p.id || p.player_id);
              return sum + (live?.current_dkfp || 0);
            }, 0);

            return (
              <div key={idx} className="bg-surface border border-border rounded-lg overflow-hidden">
                {/* Lineup Header */}
                <div className="px-4 py-3 border-b border-border flex justify-between items-center">
                  <div className="text-[13px] font-bold text-white">
                    Lineup #{idx + 1}
                  </div>
                  <div className="flex gap-4 text-xs">
                    <span>
                      <span className="text-text-muted">Live: </span>
                      <span className="text-venom font-bold">{currentTotal.toFixed(1)}</span>
                    </span>
                    <span>
                      <span className="text-text-muted">Proj: </span>
                      <span className="text-text-primary">{lineup.projected?.toFixed(1) || '—'}</span>
                    </span>
                  </div>
                </div>

                {/* Players */}
                <div className="py-2">
                  {players.map((p, pi) => {
                    const live = getPlayerScore(p.id || p.player_id);
                    const currentPts = live?.current_dkfp || 0;
                    const projPts = p.dk_points || 0;
                    const scoreColor = getScoreColor(currentPts, projPts);
                    const borderColor = getScoreBorderColor(currentPts, projPts);

                    return (
                      <div key={pi} className={`px-4 py-1.5 flex justify-between items-center border-l-[3px] ${borderColor} ml-1`}>
                        <div className="flex gap-2.5 items-center">
                          <span className="text-text-muted text-[10px] w-6">
                            {p.position}
                          </span>
                          <span className="text-white text-xs font-medium">
                            {p.name}
                          </span>
                          <span className="text-text-muted text-[10px]">
                            {p.team}
                          </span>
                        </div>
                        <div className="flex gap-3.5 text-xs">
                          <span className={`${scoreColor} font-bold`}>
                            {currentPts.toFixed(1)}
                          </span>
                          <span className="text-text-muted">
                            / {projPts.toFixed(1)}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Game Status */}
      {scores?.games && Object.keys(scores.games).length > 0 && (
        <div className="mt-5">
          <h4 className="text-text-muted text-xs font-semibold mb-2.5">
            GAME STATUS
          </h4>
          <div className="flex flex-wrap gap-2">
            {Object.values(scores.games).map((g, i) => (
              <div key={i} className={`px-3 py-1.5 rounded-md text-[11px] bg-surface border border-border ${g.status === 'Final' ? 'text-venom' : 'text-yellow-400'}`}>
                Game {g.game_pk}: {g.status || 'In Progress'}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
