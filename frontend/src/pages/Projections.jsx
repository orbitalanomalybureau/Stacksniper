import { useState, useEffect, useMemo } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, ScatterChart, Scatter, CartesianGrid, Cell } from "recharts";
import { Lock, ChevronDown, ChevronUp } from "lucide-react";
import { useAuth } from "../hooks/useAuth";
import api from "../api/client";
import { SkeletonRow } from "../components/ui/Skeleton";

const POSITIONS = ["ALL", "QB", "RB", "WR", "TE", "K", "DST"];
const WEEKS = Array.from({ length: 18 }, (_, i) => i + 1);
const SORT_OPTIONS = [
  { value: "projected_points", label: "Projected Pts" },
  { value: "salary", label: "Salary" },
  { value: "ceiling", label: "Ceiling" },
  { value: "name", label: "Name" },
];

export default function Projections() {
  const { user } = useAuth();
  const tier = user?.tier || "free";

  const [position, setPosition] = useState("ALL");
  const [week, setWeek] = useState(1);
  const [season] = useState(2025);
  const [sort, setSort] = useState("projected_points");
  const [players, setPlayers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [expandedId, setExpandedId] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api.get("/api/projections/", { params: { season, week, position: position === "ALL" ? undefined : position, sort } })
      .then((res) => { if (!cancelled) setPlayers(res.data); })
      .catch(() => { if (!cancelled) setPlayers([]); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [season, week, position, sort]);

  const top10 = useMemo(() => players.slice(0, 10).map((p) => ({
    name: p.name.split(" ").pop(),
    pts: p.projected_points,
    pos: p.position,
  })), [players]);

  const scatterData = useMemo(() => players
    .filter((p) => p.salary && p.projected_points)
    .map((p) => ({ x: p.salary, y: p.projected_points, name: p.name, pos: p.position })),
  [players]);

  const posColor = (pos) => {
    const m = { QB: "#10b981", RB: "#3b82f6", WR: "#f59e0b", TE: "#ef4444", K: "#8b5cf6", DST: "#6b7280" };
    return m[pos] || "#10b981";
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-10">
      {/* Header + Filters */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <h1 className="text-3xl font-bold">Projections</h1>
        <div className="flex flex-wrap items-center gap-3">
          <select value={week} onChange={(e) => setWeek(Number(e.target.value))}
            className="input px-3 py-1.5 text-sm">
            {WEEKS.map((w) => <option key={w} value={w}>Week {w}</option>)}
          </select>
          <div className="flex gap-1">
            {POSITIONS.map((pos) => (
              <button key={pos} onClick={() => setPosition(pos)}
                className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
                  position === pos ? "bg-venom text-surface" : "bg-surface-light text-text-muted hover:text-text-primary"
                }`}>{pos}</button>
            ))}
          </div>
          <select value={sort} onChange={(e) => setSort(e.target.value)}
            className="input px-3 py-1.5 text-sm">
            {SORT_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>
      </div>

      {/* Charts */}
      {players.length > 0 && (
        <div className="grid md:grid-cols-2 gap-6 mb-8">
          <div className="card">
            <h3 className="text-sm font-semibold text-text-muted mb-3">Top 10 Projected</h3>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={top10}>
                <XAxis dataKey="name" tick={{ fill: "#6b9a7e", fontSize: 11 }} />
                <YAxis tick={{ fill: "#6b9a7e", fontSize: 11 }} />
                <Tooltip contentStyle={{ background: "#0f2218", border: "1px solid #1a3d27", borderRadius: 8 }}
                  labelStyle={{ color: "#eaf5ee" }} itemStyle={{ color: "#00ff88" }} />
                <Bar dataKey="pts" radius={[4, 4, 0, 0]}>
                  {top10.map((entry, i) => <Cell key={i} fill={posColor(entry.pos)} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="card">
            <h3 className="text-sm font-semibold text-text-muted mb-3">Salary vs Projected Points</h3>
            <ResponsiveContainer width="100%" height={220}>
              <ScatterChart>
                <CartesianGrid strokeDasharray="3 3" stroke="#1a3d27" />
                <XAxis type="number" dataKey="x" name="Salary" tick={{ fill: "#6b9a7e", fontSize: 11 }}
                  tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
                <YAxis type="number" dataKey="y" name="Pts" tick={{ fill: "#6b9a7e", fontSize: 11 }} />
                <Tooltip cursor={{ strokeDasharray: "3 3" }}
                  contentStyle={{ background: "#0f2218", border: "1px solid #1a3d27", borderRadius: 8 }}
                  formatter={(val, name) => name === "Salary" ? `$${val.toLocaleString()}` : val.toFixed(1)} />
                <Scatter data={scatterData}>
                  {scatterData.map((entry, i) => <Cell key={i} fill={posColor(entry.pos)} />)}
                </Scatter>
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="card">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="table-header">
                <th className="text-left py-3 px-4">Player</th>
                <th className="text-left py-3 px-3">Pos</th>
                <th className="text-left py-3 px-3">Team</th>
                <th className="text-right py-3 px-3">Salary</th>
                <th className="text-right py-3 px-3">Proj</th>
                <th className="text-right py-3 px-3">{tier !== "free" ? "Floor" : <span className="flex items-center justify-end gap-1"><Lock className="w-3 h-3" />Floor</span>}</th>
                <th className="text-right py-3 px-3">{tier !== "free" ? "Ceiling" : <span className="flex items-center justify-end gap-1"><Lock className="w-3 h-3" />Ceiling</span>}</th>
                <th className="text-right py-3 px-3">{tier !== "free" ? "Value" : <span className="flex items-center justify-end gap-1"><Lock className="w-3 h-3" />Value</span>}</th>
                <th className="text-right py-3 px-3">{tier === "elite" ? "Own%" : <span className="flex items-center justify-end gap-1"><Lock className="w-3 h-3" />Own%</span>}</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                Array.from({ length: 8 }).map((_, i) => <SkeletonRow key={i} cols={9} />)
              ) : players.length === 0 ? (
                <tr><td colSpan={9} className="text-center py-12 text-text-muted">No projections available for this week.</td></tr>
              ) : players.map((p) => (
                <tr key={p.id} onClick={() => setExpandedId(expandedId === p.id ? null : p.id)}
                  className="table-row cursor-pointer">
                  <td className="py-3 px-4 font-medium text-text-primary flex items-center gap-2">
                    {p.name}
                    {expandedId === p.id ? <ChevronUp className="w-3 h-3 text-text-muted" /> : <ChevronDown className="w-3 h-3 text-text-muted" />}
                  </td>
                  <td className="py-3 px-3"><span className="px-2 py-0.5 rounded text-xs font-mono" style={{ backgroundColor: posColor(p.position) + "22", color: posColor(p.position) }}>{p.position}</span></td>
                  <td className="py-3 px-3 text-text-secondary">{p.team}</td>
                  <td className="py-3 px-3 text-right text-text-secondary">{p.salary ? `$${p.salary.toLocaleString()}` : "—"}</td>
                  <td className="py-3 px-3 text-right font-semibold text-venom">{p.projected_points.toFixed(1)}</td>
                  <td className="py-3 px-3 text-right text-text-muted">{p.floor != null ? p.floor.toFixed(1) : <span className="text-text-muted/50">—</span>}</td>
                  <td className="py-3 px-3 text-right text-text-muted">{p.ceiling != null ? p.ceiling.toFixed(1) : <span className="text-text-muted/50">—</span>}</td>
                  <td className="py-3 px-3 text-right">{p.value != null ? <span className={p.value >= 4.0 ? "text-venom" : p.value < 2.5 ? "text-fangs" : "text-text-secondary"}>{p.value.toFixed(2)}</span> : <span className="text-text-muted/50">—</span>}</td>
                  <td className="py-3 px-3 text-right text-text-muted">{p.ownership != null ? `${p.ownership.toFixed(1)}%` : <span className="text-text-muted/50">—</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Tier gate overlay for free users */}
        {tier === "free" && players.length > 0 && (
          <div className="mt-4 bg-venom/5 border border-venom/20 rounded-lg px-4 py-3 text-sm text-center">
            <Lock className="w-4 h-4 inline mr-1 text-venom" />
            <span className="text-text-secondary">Upgrade to </span>
            <a href="#/pricing" className="text-venom font-semibold hover:underline">Pro</a>
            <span className="text-text-secondary"> to unlock Floor, Ceiling, and Value columns.</span>
          </div>
        )}
      </div>

      {/* Expanded player detail */}
      {expandedId && (() => {
        const p = players.find((x) => x.id === expandedId);
        if (!p) return null;
        return (
          <div className="card mt-4 animate-fade-in">
            <h3 className="text-lg font-semibold mb-3">{p.name} <span className="text-text-muted text-sm">— {p.team} {p.position}</span></h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              {p.pass_yds != null && <div><span className="text-text-muted">Pass Yds</span><p className="font-semibold">{p.pass_yds.toFixed(0)}</p></div>}
              {p.pass_tds != null && <div><span className="text-text-muted">Pass TDs</span><p className="font-semibold">{p.pass_tds.toFixed(1)}</p></div>}
              {p.rush_yds != null && p.rush_yds > 0 && <div><span className="text-text-muted">Rush Yds</span><p className="font-semibold">{p.rush_yds.toFixed(0)}</p></div>}
              {p.rush_tds != null && p.rush_tds > 0 && <div><span className="text-text-muted">Rush TDs</span><p className="font-semibold">{p.rush_tds.toFixed(1)}</p></div>}
              {p.rec != null && p.rec > 0 && <div><span className="text-text-muted">Rec</span><p className="font-semibold">{p.rec.toFixed(1)}</p></div>}
              {p.rec_yds != null && p.rec_yds > 0 && <div><span className="text-text-muted">Rec Yds</span><p className="font-semibold">{p.rec_yds.toFixed(0)}</p></div>}
              {p.rec_tds != null && p.rec_tds > 0 && <div><span className="text-text-muted">Rec TDs</span><p className="font-semibold">{p.rec_tds.toFixed(1)}</p></div>}
              <div><span className="text-text-muted">Projected</span><p className="font-semibold text-venom">{p.projected_points.toFixed(1)}</p></div>
            </div>
          </div>
        );
      })()}
    </div>
  );
}
