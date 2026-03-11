import { useState, useEffect } from "react";
import { BarChart3, Cpu, ListOrdered, TrendingUp, Zap } from "lucide-react";
import { Link } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import api from "../api/client";
import { SkeletonCard } from "../components/ui/Skeleton";

export default function Dashboard() {
  const { user } = useAuth();
  const tierDisplay = user?.tier ? user.tier.charAt(0).toUpperCase() + user.tier.slice(1) : "Free";

  const [topPlayers, setTopPlayers] = useState({ qb: null, rb: null });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let done = 0;
    const check = () => { done++; if (done >= 2) setLoading(false); };
    api.get("/api/projections/", { params: { season: 2025, week: 1, position: "QB", sort: "projected_points" } })
      .then((res) => {
        if (res.data.length > 0) setTopPlayers((prev) => ({ ...prev, qb: res.data[0] }));
      })
      .catch(() => {})
      .finally(check);
    api.get("/api/projections/", { params: { season: 2025, week: 1, position: "RB", sort: "projected_points" } })
      .then((res) => {
        if (res.data.length > 0) setTopPlayers((prev) => ({ ...prev, rb: res.data[0] }));
      })
      .catch(() => {})
      .finally(check);
  }, []);

  return (
    <div className="max-w-7xl mx-auto px-4 py-10">
      <h1 className="text-3xl font-bold mb-2">Dashboard</h1>
      {user && <p className="text-text-muted mb-6">Welcome back, {user.display_name || user.email}</p>}

      {user?.trial_expires_at && new Date(user.trial_expires_at) > new Date() && (
        <div className="bg-venom/10 border border-venom/30 rounded-lg px-4 py-3 mb-6 text-sm text-venom">
          Pro trial active — expires {new Date(user.trial_expires_at).toLocaleDateString()}.{" "}
          <Link to="/pricing" className="underline font-semibold">Upgrade now</Link>
        </div>
      )}

      {/* Stats cards */}
      <div className="grid md:grid-cols-4 gap-4 mb-8">
        {loading ? (
          <>
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </>
        ) : (
          <>
            <div className="card">
              <div className="flex items-center justify-between mb-2">
                <span className="text-text-muted text-sm">Top QB</span>
                <TrendingUp className="w-5 h-5 text-venom" />
              </div>
              {topPlayers.qb ? (
                <>
                  <p className="text-lg font-bold">{topPlayers.qb.name}</p>
                  <p className="text-venom text-sm">{topPlayers.qb.projected_points.toFixed(1)} pts</p>
                </>
              ) : (
                <p className="text-text-muted text-sm">No data</p>
              )}
            </div>
            <div className="card">
              <div className="flex items-center justify-between mb-2">
                <span className="text-text-muted text-sm">Best Value RB</span>
                <Zap className="w-5 h-5 text-venom" />
              </div>
              {topPlayers.rb ? (
                <>
                  <p className="text-lg font-bold">{topPlayers.rb.name}</p>
                  <p className="text-venom text-sm">{topPlayers.rb.projected_points.toFixed(1)} pts</p>
                </>
              ) : (
                <p className="text-text-muted text-sm">No data</p>
              )}
            </div>
            <div className="card">
              <div className="flex items-center justify-between mb-2">
                <span className="text-text-muted text-sm">Simulations Run</span>
                <Cpu className="w-5 h-5 text-venom" />
              </div>
              <p className="text-3xl font-bold">0</p>
            </div>
            <div className="card">
              <div className="flex items-center justify-between mb-2">
                <span className="text-text-muted text-sm">Current Tier</span>
                <BarChart3 className="w-5 h-5 text-venom" />
              </div>
              <p className="text-3xl font-bold text-venom">{tierDisplay}</p>
            </div>
          </>
        )}
      </div>

      {/* Quick links */}
      <div className="grid md:grid-cols-3 gap-6">
        <Link to="/projections" className="card-hover group">
          <h3 className="text-lg font-semibold mb-2 group-hover:text-venom transition-colors">View Projections</h3>
          <p className="text-text-muted text-sm">Browse player projections for the current week.</p>
        </Link>
        <Link to="/simulator" className="card-hover group">
          <h3 className="text-lg font-semibold mb-2 group-hover:text-venom transition-colors">Run Simulation</h3>
          <p className="text-text-muted text-sm">Start a Monte Carlo simulation for contest analysis.</p>
        </Link>
        <Link to="/lineups" className="card-hover group">
          <h3 className="text-lg font-semibold mb-2 group-hover:text-venom transition-colors">Optimize Lineups</h3>
          <p className="text-text-muted text-sm">Generate optimal DFS lineups with our optimizer.</p>
        </Link>
      </div>
    </div>
  );
}
