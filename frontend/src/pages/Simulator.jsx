import { useState, useMemo } from "react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  ScatterChart, Scatter, CartesianGrid, Cell,
} from "recharts";
import { Cpu, TrendingUp, TrendingDown, Target, Zap, ChevronDown, ChevronUp, Download } from "lucide-react";
import { useAuth } from "../hooks/useAuth";
import api from "../api/client";

const WEEKS = Array.from({ length: 18 }, (_, i) => i + 1);

const posColor = (pos) => {
  const m = { QB: "#10b981", RB: "#3b82f6", WR: "#f59e0b", TE: "#ef4444", K: "#8b5cf6", DST: "#6b7280" };
  return m[pos] || "#10b981";
};

export default function Simulator() {
  const { user } = useAuth();
  const tier = user?.tier || "free";

  const [week, setWeek] = useState(1);
  const [season] = useState(2025);
  const [platform, setPlatform] = useState("draftkings");
  const [contestType, setContestType] = useState("gpp");
  const maxSims = tier === "elite" ? 10000 : tier === "pro" ? 5000 : 1000;
  const [numSims, setNumSims] = useState(maxSims);

  const [running, setRunning] = useState(false);
  const [simId, setSimId] = useState(null);
  const [results, setResults] = useState(null);
  const [lineups, setLineups] = useState([]);
  const [expandedLineup, setExpandedLineup] = useState(null);
  const [sortCol, setSortCol] = useState("avg_points");
  const [sortAsc, setSortAsc] = useState(false);
  const [error, setError] = useState(null);

  const handleRun = async () => {
    setRunning(true);
    setError(null);
    setResults(null);
    setLineups([]);
    setSimId(null);

    try {
      const { data: simRun } = await api.post("/api/simulations/", {
        season,
        week,
        num_sims: numSims,
        platform,
        contest_type: contestType,
      });
      setSimId(simRun.id);

      if (simRun.status === "completed") {
        await fetchResults(simRun.id);
      } else {
        await pollStatus(simRun.id);
      }
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to start simulation");
      setRunning(false);
    }
  };

  const pollStatus = async (id) => {
    for (let i = 0; i < 30; i++) {
      await new Promise((r) => setTimeout(r, 2000));
      try {
        const { data } = await api.get(`/api/simulations/${id}`);
        if (data.status === "completed") { await fetchResults(id); return; }
        if (data.status === "failed") { setError("Simulation failed."); setRunning(false); return; }
      } catch { break; }
    }
    setError("Simulation timed out.");
    setRunning(false);
  };

  const fetchResults = async (id) => {
    try {
      const { data } = await api.get(`/api/simulations/${id}/results`);
      setResults(data);
      try {
        const { data: lus } = await api.get(`/api/lineups/${id}/lineups?num=20`);
        setLineups(lus);
      } catch { /* lineups optional */ }
    } catch {
      setError("Failed to load results");
    } finally {
      setRunning(false);
    }
  };

  const sortedPlayers = useMemo(() => {
    if (!results?.players) return [];
    const arr = [...results.players];
    arr.sort((a, b) => sortAsc ? (a[sortCol] ?? 0) - (b[sortCol] ?? 0) : (b[sortCol] ?? 0) - (a[sortCol] ?? 0));
    return arr;
  }, [results, sortCol, sortAsc]);

  const toggleSort = (col) => {
    if (sortCol === col) setSortAsc(!sortAsc);
    else { setSortCol(col); setSortAsc(false); }
  };

  const scatterData = useMemo(() => {
    if (!results?.players) return [];
    return results.players.map((p) => ({ x: p.salary, y: p.avg_points, name: p.name, pos: p.position }));
  }, [results]);

  const stackData = useMemo(() => {
    if (!results?.stacks) return [];
    return results.stacks.slice(0, 8).map((s) => ({
      name: `${s.player_1.split(" ").pop()}+${s.player_2.split(" ").pop()}`,
      freq: s.frequency,
    }));
  }, [results]);

  return (
    <div className="max-w-7xl mx-auto px-4 py-10">
      <h1 className="text-3xl font-bold mb-6">Monte Carlo Simulator</h1>

      <div className="grid lg:grid-cols-4 gap-6">
        {/* Config Panel */}
        <div className="card lg:col-span-1 space-y-4">
          <h2 className="text-lg font-semibold">Configuration</h2>

          <div>
            <label className="block text-sm text-text-muted mb-1">Week</label>
            <select value={week} onChange={(e) => setWeek(Number(e.target.value))}
              className="input px-3 py-1.5 text-sm w-full">
              {WEEKS.map((w) => <option key={w} value={w}>Week {w}</option>)}
            </select>
          </div>

          <div>
            <label className="block text-sm text-text-muted mb-1">Platform</label>
            <div className="flex gap-2">
              {["draftkings", "fanduel"].map((p) => (
                <button key={p} onClick={() => setPlatform(p)}
                  className={`flex-1 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                    platform === p ? "bg-venom text-surface" : "bg-surface-light text-text-muted hover:text-text-primary"
                  }`}>{p === "draftkings" ? "DraftKings" : "FanDuel"}</button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm text-text-muted mb-1">Contest Type</label>
            <div className="flex gap-2">
              {[["gpp", "GPP"], ["cash", "Cash"]].map(([val, label]) => (
                <button key={val} onClick={() => setContestType(val)}
                  className={`flex-1 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                    contestType === val ? "bg-venom text-surface" : "bg-surface-light text-text-muted hover:text-text-primary"
                  }`}>{label}</button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm text-text-muted mb-1">Simulations: {numSims.toLocaleString()}</label>
            <input type="range" min={500} max={maxSims} step={500}
              value={numSims} onChange={(e) => setNumSims(Number(e.target.value))}
              className="w-full accent-venom" />
            <div className="flex justify-between text-xs text-text-muted mt-1">
              <span>500</span><span>{(maxSims / 1000).toFixed(0)}K</span>
            </div>
          </div>

          <button onClick={handleRun} disabled={running}
            className="btn-primary w-full flex items-center justify-center gap-2">
            <Cpu className="w-4 h-4" />
            {running ? "Running..." : "Run Simulation"}
          </button>

          {error && (
            <div className="bg-fangs/10 border border-fangs/30 rounded-lg px-3 py-2 text-sm text-fangs">{error}</div>
          )}
        </div>

        {/* Results */}
        <div className="lg:col-span-3 space-y-6">
          {!results && !running && (
            <div className="card text-center py-16 text-text-muted">
              <Cpu className="w-16 h-16 mx-auto mb-4 opacity-20" />
              <p className="text-lg">Configure and run a simulation to see results.</p>
              <p className="text-sm mt-1">Monte Carlo simulations model thousands of possible outcomes.</p>
            </div>
          )}

          {running && (
            <div className="card text-center py-16">
              <div className="animate-spin w-12 h-12 border-4 border-venom border-t-transparent rounded-full mx-auto mb-4" />
              <p className="text-lg text-text-secondary">Running {numSims.toLocaleString()} simulations...</p>
              <p className="text-sm text-text-muted mt-1">This may take a few seconds.</p>
            </div>
          )}

          {results && (
            <>
              {/* Summary Cards */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="card text-center">
                  <Zap className="w-5 h-5 mx-auto mb-1 text-venom" />
                  <p className="text-2xl font-bold text-venom">{results.num_sims?.toLocaleString()}</p>
                  <p className="text-xs text-text-muted">Simulations</p>
                </div>
                <div className="card text-center">
                  <Target className="w-5 h-5 mx-auto mb-1 text-blue-400" />
                  <p className="text-2xl font-bold text-blue-400">{results.lineup_score_avg?.toFixed(1) || "—"}</p>
                  <p className="text-xs text-text-muted">Avg Best Lineup</p>
                </div>
                <div className="card text-center">
                  <TrendingUp className="w-5 h-5 mx-auto mb-1 text-venom" />
                  <p className="text-2xl font-bold text-venom">{results.lineup_score_p90?.toFixed(1) || "—"}</p>
                  <p className="text-xs text-text-muted">90th Pctl Lineup</p>
                </div>
                <div className="card text-center">
                  <TrendingDown className="w-5 h-5 mx-auto mb-1 text-gold" />
                  <p className="text-2xl font-bold text-gold">{results.stacks?.[0]?.frequency?.toFixed(1) || "—"}%</p>
                  <p className="text-xs text-text-muted">Top Stack Freq</p>
                </div>
              </div>

              {/* Charts */}
              <div className="grid md:grid-cols-2 gap-6">
                <div className="card">
                  <h3 className="text-sm font-semibold text-text-muted mb-3">Salary vs Sim Avg Points</h3>
                  <ResponsiveContainer width="100%" height={220}>
                    <ScatterChart>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1a3d27" />
                      <XAxis type="number" dataKey="x" name="Salary" tick={{ fill: "#6b9a7e", fontSize: 11 }}
                        tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
                      <YAxis type="number" dataKey="y" name="Avg Pts" tick={{ fill: "#6b9a7e", fontSize: 11 }} />
                      <Tooltip cursor={{ strokeDasharray: "3 3" }}
                        contentStyle={{ background: "#0f2218", border: "1px solid #1a3d27", borderRadius: 8 }}
                        formatter={(val, name) => name === "Salary" ? `$${val.toLocaleString()}` : val.toFixed(1)} />
                      <Scatter data={scatterData}>
                        {scatterData.map((e, i) => <Cell key={i} fill={posColor(e.pos)} />)}
                      </Scatter>
                    </ScatterChart>
                  </ResponsiveContainer>
                </div>
                <div className="card">
                  <h3 className="text-sm font-semibold text-text-muted mb-3">Top Stacks</h3>
                  <ResponsiveContainer width="100%" height={220}>
                    <BarChart data={stackData}>
                      <XAxis dataKey="name" tick={{ fill: "#6b9a7e", fontSize: 10 }} />
                      <YAxis tick={{ fill: "#6b9a7e", fontSize: 11 }} tickFormatter={(v) => `${v}%`} />
                      <Tooltip contentStyle={{ background: "#0f2218", border: "1px solid #1a3d27", borderRadius: 8 }}
                        formatter={(v) => `${v.toFixed(1)}%`} />
                      <Bar dataKey="freq" fill="#00ff88" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Player Table */}
              <div className="card">
                <h3 className="text-sm font-semibold text-text-muted mb-3">Player Simulation Results</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="table-header">
                        <th className="text-left py-2 px-3">Player</th>
                        <th className="text-left py-2 px-2">Pos</th>
                        <th className="text-right py-2 px-2 cursor-pointer hover:text-text-primary" onClick={() => toggleSort("salary")}>Salary</th>
                        <th className="text-right py-2 px-2 cursor-pointer hover:text-text-primary" onClick={() => toggleSort("avg_points")}>
                          Avg {sortCol === "avg_points" && (sortAsc ? "↑" : "↓")}
                        </th>
                        <th className="text-right py-2 px-2 cursor-pointer hover:text-text-primary" onClick={() => toggleSort("floor")}>Floor</th>
                        <th className="text-right py-2 px-2 cursor-pointer hover:text-text-primary" onClick={() => toggleSort("ceiling")}>Ceil</th>
                        <th className="text-right py-2 px-2 cursor-pointer hover:text-text-primary" onClick={() => toggleSort("boom_rate")}>
                          Boom% {sortCol === "boom_rate" && (sortAsc ? "↑" : "↓")}
                        </th>
                        <th className="text-right py-2 px-2 cursor-pointer hover:text-text-primary" onClick={() => toggleSort("bust_rate")}>Bust%</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sortedPlayers.map((p) => (
                        <tr key={p.player_id} className="table-row">
                          <td className="py-2 px-3 font-medium text-text-primary">{p.name}</td>
                          <td className="py-2 px-2">
                            <span className="px-2 py-0.5 rounded text-xs font-mono" style={{ backgroundColor: posColor(p.position) + "22", color: posColor(p.position) }}>{p.position}</span>
                          </td>
                          <td className="py-2 px-2 text-right text-text-secondary">${p.salary?.toLocaleString()}</td>
                          <td className="py-2 px-2 text-right font-semibold text-venom">{p.avg_points?.toFixed(1)}</td>
                          <td className="py-2 px-2 text-right text-text-muted">{p.floor?.toFixed(1)}</td>
                          <td className="py-2 px-2 text-right text-text-muted">{p.ceiling?.toFixed(1)}</td>
                          <td className="py-2 px-2 text-right">
                            <span className={p.boom_rate >= 10 ? "text-venom" : "text-text-muted"}>{p.boom_rate?.toFixed(1)}%</span>
                          </td>
                          <td className="py-2 px-2 text-right">
                            <span className={p.bust_rate >= 30 ? "text-fangs" : "text-text-muted"}>{p.bust_rate?.toFixed(1)}%</span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Lineups */}
              {lineups.length > 0 && (
                <div className="card">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-semibold text-text-muted">Top {lineups.length} Optimized Lineups</h3>
                    {simId && (
                      <a href={`${api.defaults.baseURL}/api/lineups/${simId}/export?platform=${platform}&num=20`}
                        target="_blank" rel="noopener noreferrer"
                        className="flex items-center gap-1 text-xs text-venom hover:underline">
                        <Download className="w-3 h-3" /> Export CSV
                      </a>
                    )}
                  </div>
                  <div className="space-y-2">
                    {lineups.map((lu, idx) => (
                      <div key={idx} className="border border-border rounded-lg">
                        <button onClick={() => setExpandedLineup(expandedLineup === idx ? null : idx)}
                          className="w-full flex items-center justify-between px-4 py-2 hover:bg-surface/50 transition-colors text-left">
                          <span className="font-mono text-sm">
                            <span className="text-text-muted">#{idx + 1}</span>
                            <span className="text-text-primary ml-3">{lu.total_projected?.toFixed(1)} pts</span>
                            <span className="text-text-muted ml-3">${lu.total_salary?.toLocaleString()}</span>
                          </span>
                          {expandedLineup === idx ? <ChevronUp className="w-4 h-4 text-text-muted" /> : <ChevronDown className="w-4 h-4 text-text-muted" />}
                        </button>
                        {expandedLineup === idx && (
                          <div className="px-4 pb-3 grid grid-cols-3 md:grid-cols-5 gap-2 text-xs">
                            {lu.players?.map((p, pi) => (
                              <div key={pi} className="bg-surface rounded px-2 py-1">
                                <span className="font-mono text-xs mr-1" style={{ color: posColor(p.position) }}>{p.position}</span>
                                <span className="text-text-primary">{p.name?.split(" ").pop()}</span>
                                <span className="text-text-muted ml-1">${(p.salary || 0).toLocaleString()}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
