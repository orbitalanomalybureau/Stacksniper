import { useState, useEffect, useCallback } from "react";
import api from "../api/client";

// MLB-specific components (lazy-loaded)
import ControlBar from "../components/MLB/ControlBar";
import TabNav from "../components/MLB/TabNav";
import ScheduleView from "../components/MLB/ScheduleView";
import ProjectionsTable from "../components/MLB/ProjectionsTable";
import LineupsView from "../components/MLB/LineupsView";
import StacksView from "../components/MLB/StacksView";
import GameHeatmap from "../components/MLB/GameHeatmap";
import ExposureCharts from "../components/MLB/ExposureCharts";
import IntelBrief from "../components/MLB/IntelBrief";
import BacktestView from "../components/MLB/BacktestView";
import LiveView from "../components/MLB/LiveView";
import ContestManager from "../components/MLB/ContestManager";
import PropsView from "../components/MLB/PropsView";
import PlayerModal from "../components/MLB/PlayerModal";
import PlayerCompare from "../components/MLB/PlayerCompare";
import CoPilotPanel from "../components/MLB/CoPilotPanel";
import LineupBuilder from "../components/MLB/LineupBuilder";
import SettingsPanel from "../components/MLB/SettingsPanel";
import LoadingSkeleton from "../components/MLB/LoadingSkeleton";

const API = "/api/mlb";

const STORAGE_KEYS = {
  simDate: "stacksniper_mlb_simDate",
  numSims: "stacksniper_mlb_numSims",
  contestType: "stacksniper_mlb_contestType",
  tab: "stacksniper_mlb_tab",
};

export default function MLBDashboard() {
  const [tab, setTab] = useState(() => {
    try { return localStorage.getItem(STORAGE_KEYS.tab) || "schedule"; } catch { return "schedule"; }
  });
  const [schedule, setSchedule] = useState([]);
  const [simResult, setSimResult] = useState(null);
  const [lineups, setLineups] = useState(null);
  const [stacks, setStacks] = useState(null);
  const [brief, setBrief] = useState(null);
  const [loading, setLoading] = useState(false);
  const [briefLoading, setBriefLoading] = useState(false);
  const [numSims, setNumSims] = useState(() => {
    try { const v = localStorage.getItem(STORAGE_KEYS.numSims); return v ? parseInt(v, 10) : 500; } catch { return 500; }
  });
  const [contestType, setContestType] = useState(() => {
    try { return localStorage.getItem(STORAGE_KEYS.contestType) || "gpp"; } catch { return "gpp"; }
  });
  const [simDate, setSimDate] = useState(() => {
    try { return localStorage.getItem(STORAGE_KEYS.simDate) || new Date().toISOString().split("T")[0]; } catch { return new Date().toISOString().split("T")[0]; }
  });
  const [error, setError] = useState(null);
  const [selectedPlayer, setSelectedPlayer] = useState(null);
  const [locks, setLocks] = useState([]);
  const [excludes, setExcludes] = useState([]);
  const [comparePlayers, setComparePlayers] = useState([]);
  const [copilotOpen, setCopilotOpen] = useState(false);
  const [editingLineup, setEditingLineup] = useState(null);

  // Persist to localStorage
  useEffect(() => { try { localStorage.setItem(STORAGE_KEYS.simDate, simDate); } catch {} }, [simDate]);
  useEffect(() => { try { localStorage.setItem(STORAGE_KEYS.numSims, String(numSims)); } catch {} }, [numSims]);
  useEffect(() => { try { localStorage.setItem(STORAGE_KEYS.contestType, contestType); } catch {} }, [contestType]);
  useEffect(() => { try { localStorage.setItem(STORAGE_KEYS.tab, tab); } catch {} }, [tab]);

  useEffect(() => { fetchSchedule(); }, [simDate]);

  // Keyboard shortcuts
  useEffect(() => {
    const TABS_ORDER = ["schedule", "heatmap", "projections", "props", "lineups", "stacks", "intel", "live", "portfolio", "backtest", "settings"];

    const handleKeyDown = (e) => {
      const tag = e.target.tagName.toLowerCase();
      if (tag === "input" || tag === "textarea" || tag === "select") return;

      if (e.key >= "1" && e.key <= "9") {
        const idx = parseInt(e.key, 10) - 1;
        if (idx < TABS_ORDER.length) { e.preventDefault(); setTab(TABS_ORDER[idx]); }
        return;
      }
      if (e.key === "0") { e.preventDefault(); setTab(TABS_ORDER[9]); return; }
      if (e.key === "r" && !e.metaKey && !e.ctrlKey) { e.preventDefault(); runSimulation(); return; }
      if (e.key === "l" && !e.metaKey && !e.ctrlKey) { e.preventDefault(); generateLineups(); return; }
      if (e.key === "c" && !e.metaKey && !e.ctrlKey) { e.preventDefault(); setCopilotOpen(prev => !prev); return; }
      if (e.key === "Escape") { setSelectedPlayer(null); setCopilotOpen(false); }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [numSims, simDate, contestType, locks, excludes]);

  const fetchSchedule = useCallback(async () => {
    try {
      const res = await api.get(`${API}/schedule?date=${simDate}`);
      setSchedule(res.data.games || []);
    } catch {
      setError("Failed to load schedule");
    }
  }, [simDate]);

  const runSimulation = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.post(`${API}/simulate`, { num_sims: numSims, date: simDate });
      if (res.data.error) throw new Error(res.data.error);
      setSimResult(res.data);
      setLineups(null);
      setStacks(null);
      setTab("projections");
    } catch (e) {
      setError("Simulation failed: " + (e.response?.data?.detail || e.message));
    }
    setLoading(false);
  }, [numSims, simDate]);

  const generateLineups = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.post(`${API}/optimize`, {
        num_lineups: 20,
        max_exposure: 0.6,
        contest_type: contestType,
        locks,
        excludes,
      });
      if (res.data.error) throw new Error(res.data.error);
      setLineups(res.data.lineups || []);
      setStacks(res.data.top_stacks || []);
      setTab("lineups");
    } catch (e) {
      setError("Optimization failed: " + (e.response?.data?.detail || e.message));
    }
    setLoading(false);
  }, [contestType, locks, excludes]);

  const generateBrief = useCallback(async () => {
    setBriefLoading(true);
    try {
      const res = await api.post(`${API}/news/brief`, { date: simDate });
      if (res.data.error) {
        setError(res.data.error);
      } else {
        setBrief(res.data);
      }
      setTab("intel");
    } catch (e) {
      setError("Failed to generate brief: " + (e.response?.data?.detail || e.message));
    }
    setBriefLoading(false);
  }, [simDate]);

  const exportCSV = useCallback(async () => {
    try {
      const res = await api.post(`${API}/export/dk-csv`, {}, { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement("a");
      a.href = url;
      a.download = `stacksniper_mlb_lineups_${simDate}.csv`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch {
      setError("Export failed");
    }
  }, [simDate]);

  const handleToggleLock = (playerId) => {
    setLocks(prev => prev.includes(playerId) ? prev.filter(id => id !== playerId) : [...prev, playerId]);
    setExcludes(prev => prev.filter(id => id !== playerId));
  };

  const handleToggleExclude = (playerId) => {
    setExcludes(prev => prev.includes(playerId) ? prev.filter(id => id !== playerId) : [...prev, playerId]);
    setLocks(prev => prev.filter(id => id !== playerId));
  };

  const handleComparePlayer = (player) => {
    setComparePlayers(prev => {
      const exists = prev.find(p => (p.id || p.name) === (player.id || player.name));
      if (exists) return prev.filter(p => (p.id || p.name) !== (player.id || player.name));
      if (prev.length >= 4) return [...prev.slice(1), player];
      return [...prev, player];
    });
  };

  const handleRemoveComparePlayer = (playerId) => {
    setComparePlayers(prev => prev.filter(p => (p.id || p.name) !== playerId));
  };

  const handleCoPilotAction = (action, playerId) => {
    if (action === "lock") handleToggleLock(playerId);
    else if (action === "exclude") handleToggleExclude(playerId);
  };

  return (
    <div className="max-w-[1600px] mx-auto px-4 sm:px-8 py-6">
      <ControlBar
        simDate={simDate}
        setSimDate={setSimDate}
        numSims={numSims}
        setNumSims={setNumSims}
        contestType={contestType}
        setContestType={setContestType}
        onRunSimulation={runSimulation}
        onGenerateLineups={generateLineups}
        onGenerateBrief={generateBrief}
        loading={loading}
        simResult={simResult}
      />

      {error && (
        <div className="px-5 py-3 bg-fangs/10 border border-fangs rounded-md mb-5 text-xs text-fangs flex justify-between items-center animate-fade-in">
          {error}
          <span className="cursor-pointer text-fangs hover:text-fangs/70" onClick={() => setError(null)}>&times;</span>
        </div>
      )}

      {/* Summary Cards */}
      {simResult && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
          {[
            { label: "Simulations", value: simResult.num_sims?.toLocaleString(), color: "text-venom" },
            { label: "Games", value: simResult.games_count, color: "text-blue-400" },
            { label: "Players", value: simResult.players_count, color: "text-venom-glow" },
            { label: "Confidence", value: simResult.confidence ? `${(simResult.confidence * 100).toFixed(0)}%` : "\u2014", color: "text-purple-400" },
          ].map(c => (
            <div key={c.label} className="bg-surface rounded-lg p-5 border border-border">
              <div className="text-text-muted text-[10px] tracking-widest uppercase mb-1.5">{c.label}</div>
              <div className={`text-[28px] font-extrabold ${c.color}`}>{c.value}</div>
            </div>
          ))}
        </div>
      )}

      <TabNav tab={tab} setTab={setTab} />

      <div className="text-[10px] text-text-muted/40 tracking-wider mb-4">
        KEYS: 1-0 switch tabs / R run sim / L gen lineups / C copilot / ESC close
      </div>

      {loading && <LoadingSkeleton type={tab === "projections" ? "table" : "card"} />}

      {!loading && tab === "schedule" && <ScheduleView schedule={schedule} date={simDate} />}
      {!loading && tab === "heatmap" && <GameHeatmap games={simResult?.game_environments || simResult?.games || schedule} />}
      {!loading && tab === "projections" && (
        <>
          <ProjectionsTable
            simResult={simResult}
            onPlayerClick={setSelectedPlayer}
            locks={locks}
            excludes={excludes}
            onToggleLock={handleToggleLock}
            onToggleExclude={handleToggleExclude}
            onComparePlayer={handleComparePlayer}
          />
          {comparePlayers.length > 0 && (
            <PlayerCompare players={comparePlayers} onRemovePlayer={handleRemoveComparePlayer} />
          )}
        </>
      )}
      {!loading && tab === "props" && <PropsView simId={simResult?.sim_id} />}
      {!loading && tab === "lineups" && (
        <>
          {editingLineup ? (
            <LineupBuilder
              lineup={editingLineup}
              allPlayers={simResult?.players || []}
              onSave={() => setEditingLineup(null)}
              onReset={() => setEditingLineup(null)}
            />
          ) : (
            <>
              <LineupsView lineups={lineups} onExportCSV={lineups?.length > 0 ? exportCSV : null} />
              <ExposureCharts lineups={lineups} />
            </>
          )}
        </>
      )}
      {!loading && tab === "stacks" && <StacksView stacks={stacks} />}
      {tab === "intel" && <IntelBrief brief={brief} onGenerate={generateBrief} loading={briefLoading} />}
      {tab === "live" && <LiveView lineups={lineups} simResult={simResult} />}
      {tab === "portfolio" && (
        <ContestManager simResult={simResult} onLineups={(data) => {
          if (data?.gpp_multi) setLineups(data.gpp_multi);
        }} />
      )}
      {tab === "backtest" && <BacktestView />}
      {tab === "settings" && <SettingsPanel />}

      {selectedPlayer && <PlayerModal player={selectedPlayer} onClose={() => setSelectedPlayer(null)} />}
      <CoPilotPanel isOpen={copilotOpen} onClose={() => setCopilotOpen(false)} onAction={handleCoPilotAction} />
    </div>
  );
}
