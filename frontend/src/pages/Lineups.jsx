import { useState } from "react";
import { ListOrdered, Download, ChevronDown, ChevronUp } from "lucide-react";
import { useAuth } from "../hooks/useAuth";
import api from "../api/client";

const WEEKS = Array.from({ length: 18 }, (_, i) => i + 1);

const posColor = (pos) => {
  const m = { QB: "#10b981", RB: "#3b82f6", WR: "#f59e0b", TE: "#ef4444", K: "#8b5cf6", DST: "#6b7280" };
  return m[pos] || "#10b981";
};

export default function Lineups() {
  const { user } = useAuth();

  const [week, setWeek] = useState(1);
  const [season] = useState(2025);
  const [platform, setPlatform] = useState("draftkings");
  const [contestType, setContestType] = useState("gpp");
  const [numLineups, setNumLineups] = useState(20);

  const [lineups, setLineups] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [expandedIdx, setExpandedIdx] = useState(null);
  const [compareA, setCompareA] = useState(null);
  const [compareB, setCompareB] = useState(null);

  const handleGenerate = async () => {
    setLoading(true);
    setError(null);
    setLineups([]);
    setCompareA(null);
    setCompareB(null);

    try {
      const { data } = await api.post("/api/lineups/optimize", {
        season,
        week,
        platform,
        contest_type: contestType,
        num_lineups: numLineups,
      });
      setLineups(data);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to generate lineups");
    } finally {
      setLoading(false);
    }
  };

  const handleExportCSV = () => {
    if (!lineups.length) return;
    const platformConfig = platform === "fanduel"
      ? { header: ["QB", "RB", "RB", "WR", "WR", "WR", "TE", "K", "D"], flex: [] }
      : { header: ["QB", "RB", "RB", "WR", "WR", "WR", "TE", "FLEX", "DST"], flex: ["RB", "WR", "TE"] };

    let csv = platformConfig.header.join(",") + "\n";
    for (const lu of lineups) {
      const players = [...lu.players];
      const row = [];
      const used = new Set();
      for (const slot of platformConfig.header) {
        let found = false;
        if (slot === "FLEX") {
          for (let i = 0; i < players.length; i++) {
            if (!used.has(i) && platformConfig.flex.includes(players[i].position)) {
              row.push(players[i].name);
              used.add(i);
              found = true;
              break;
            }
          }
        } else if (slot === "D") {
          for (let i = 0; i < players.length; i++) {
            if (!used.has(i) && players[i].position === "DST") {
              row.push(players[i].name);
              used.add(i);
              found = true;
              break;
            }
          }
        } else {
          for (let i = 0; i < players.length; i++) {
            if (!used.has(i) && players[i].position === slot) {
              row.push(players[i].name);
              used.add(i);
              found = true;
              break;
            }
          }
        }
        if (!found) row.push("");
      }
      csv += row.join(",") + "\n";
    }

    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `lineups_${platform}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const comparisonData = (() => {
    if (compareA == null || compareB == null) return null;
    const luA = lineups[compareA];
    const luB = lineups[compareB];
    if (!luA || !luB) return null;

    const namesA = new Set(luA.players.map((p) => p.name));
    const namesB = new Set(luB.players.map((p) => p.name));
    const shared = [...namesA].filter((n) => namesB.has(n));
    const onlyA = [...namesA].filter((n) => !namesB.has(n));
    const onlyB = [...namesB].filter((n) => !namesA.has(n));

    return { shared, onlyA, onlyB, overlapPct: Math.round((shared.length / luA.players.length) * 100) };
  })();

  return (
    <div className="max-w-7xl mx-auto px-4 py-10">
      <h1 className="text-3xl font-bold mb-6">Lineup Optimizer</h1>

      <div className="grid lg:grid-cols-4 gap-6">
        {/* Settings Panel */}
        <div className="card lg:col-span-1 space-y-4">
          <h2 className="text-lg font-semibold">Settings</h2>

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
            <label className="block text-sm text-text-muted mb-1">Number of Lineups</label>
            <input type="number" value={numLineups}
              onChange={(e) => setNumLineups(Math.min(150, Math.max(1, Number(e.target.value))))}
              min={1} max={150}
              className="input px-3 py-1.5 text-sm w-full" />
          </div>

          <button onClick={handleGenerate} disabled={loading}
            className="btn-primary w-full flex items-center justify-center gap-2">
            <ListOrdered className="w-4 h-4" />
            {loading ? "Generating..." : "Generate Lineups"}
          </button>

          {lineups.length > 0 && (
            <button onClick={handleExportCSV}
              className="btn-secondary w-full flex items-center justify-center gap-2">
              <Download className="w-4 h-4" /> Export CSV ({platform === "draftkings" ? "DK" : "FD"})
            </button>
          )}

          {error && (
            <div className="bg-fangs/10 border border-fangs/30 rounded-lg px-3 py-2 text-sm text-fangs">{error}</div>
          )}
        </div>

        {/* Lineups Display */}
        <div className="lg:col-span-3 space-y-6">
          {!lineups.length && !loading && (
            <div className="card text-center py-16 text-text-muted">
              <ListOrdered className="w-16 h-16 mx-auto mb-4 opacity-20" />
              <p className="text-lg">Configure settings and generate optimized lineups.</p>
              <p className="text-sm mt-1">Uses MILP optimization to find salary-cap-optimal rosters.</p>
            </div>
          )}

          {loading && (
            <div className="card text-center py-16">
              <div className="animate-spin w-12 h-12 border-4 border-venom border-t-transparent rounded-full mx-auto mb-4" />
              <p className="text-lg text-text-secondary">Optimizing {numLineups} lineups...</p>
            </div>
          )}

          {lineups.length > 0 && (
            <>
              <div className="card">
                <h3 className="text-sm font-semibold text-text-muted mb-3">{lineups.length} Optimized Lineups</h3>
                <div className="space-y-2">
                  {lineups.map((lu, idx) => (
                    <div key={idx} className="border border-border rounded-lg">
                      <div className="flex items-center">
                        <button onClick={() => setExpandedIdx(expandedIdx === idx ? null : idx)}
                          className="flex-1 flex items-center justify-between px-4 py-2 hover:bg-surface/50 transition-colors text-left">
                          <span className="font-mono text-sm">
                            <span className="text-text-muted">#{idx + 1}</span>
                            <span className="text-text-primary ml-3">{lu.total_projected?.toFixed(1)} pts</span>
                            <span className="text-text-muted ml-3">${lu.total_salary?.toLocaleString()}</span>
                            <span className="text-text-muted/50 ml-3 text-xs">
                              {lu.players?.map((p) => p.position).join(" ")}
                            </span>
                          </span>
                          {expandedIdx === idx ? <ChevronUp className="w-4 h-4 text-text-muted" /> : <ChevronDown className="w-4 h-4 text-text-muted" />}
                        </button>
                        <div className="flex gap-1 pr-3">
                          <button onClick={() => setCompareA(idx)}
                            className={`text-xs px-2 py-0.5 rounded ${compareA === idx ? "bg-blue-500/30 text-blue-400" : "bg-surface text-text-muted hover:text-text-secondary"}`}>A</button>
                          <button onClick={() => setCompareB(idx)}
                            className={`text-xs px-2 py-0.5 rounded ${compareB === idx ? "bg-purple-500/30 text-purple-400" : "bg-surface text-text-muted hover:text-text-secondary"}`}>B</button>
                        </div>
                      </div>
                      {expandedIdx === idx && (
                        <div className="px-4 pb-3">
                          <table className="w-full text-xs">
                            <thead>
                              <tr className="text-text-muted">
                                <th className="text-left py-1">Pos</th>
                                <th className="text-left py-1">Player</th>
                                <th className="text-left py-1">Team</th>
                                <th className="text-right py-1">Salary</th>
                                <th className="text-right py-1">Proj</th>
                              </tr>
                            </thead>
                            <tbody>
                              {lu.players?.map((p, pi) => (
                                <tr key={pi} className="border-t border-border/30">
                                  <td className="py-1"><span className="font-mono" style={{ color: posColor(p.position) }}>{p.position}</span></td>
                                  <td className="py-1 text-text-primary">{p.name}</td>
                                  <td className="py-1 text-text-muted">{p.team}</td>
                                  <td className="py-1 text-right text-text-muted">${(p.salary || 0).toLocaleString()}</td>
                                  <td className="py-1 text-right text-venom">{p.projected_points?.toFixed(1)}</td>
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

              {/* Comparison */}
              {comparisonData && (
                <div className="card animate-fade-in">
                  <h3 className="text-sm font-semibold text-text-muted mb-3">
                    Lineup Comparison: #{(compareA || 0) + 1} vs #{(compareB || 0) + 1}
                    <span className="ml-2 text-venom">{comparisonData.overlapPct}% overlap</span>
                  </h3>
                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div>
                      <p className="text-xs text-blue-400 font-semibold mb-2">Only in #{(compareA || 0) + 1}</p>
                      {comparisonData.onlyA.map((n) => <p key={n} className="text-text-secondary">{n}</p>)}
                    </div>
                    <div>
                      <p className="text-xs text-venom font-semibold mb-2">Shared</p>
                      {comparisonData.shared.map((n) => <p key={n} className="text-text-primary">{n}</p>)}
                    </div>
                    <div>
                      <p className="text-xs text-purple-400 font-semibold mb-2">Only in #{(compareB || 0) + 1}</p>
                      {comparisonData.onlyB.map((n) => <p key={n} className="text-text-secondary">{n}</p>)}
                    </div>
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
