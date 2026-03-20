import { useState } from "react";
import { Outlet, Link, useLocation } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";
import { useSport } from "../../context/SportContext";
import { BarChart3, Cpu, ListOrdered, CreditCard, LogOut, Menu, X, LayoutDashboard, Repeat } from "lucide-react";
import Logo, { TextLogo } from "../Logo";

const TIER_STYLES = {
  elite: "badge-elite",
  pro: "badge-pro",
  free: "badge-free",
};

function SportSwitcher() {
  const { sport, setSport, SPORTS } = useSport();

  return (
    <div className="flex items-center bg-surface rounded-full border border-border p-0.5 gap-0.5">
      {Object.values(SPORTS).map((s) => (
        <button
          key={s.key}
          onClick={() => setSport(s.key)}
          className={`px-3 py-1 rounded-full text-xs font-semibold tracking-wider transition-all ${
            sport === s.key
              ? "bg-venom/20 text-venom border border-venom/30"
              : "text-text-muted hover:text-text-secondary border border-transparent"
          }`}
        >
          {s.label}
        </button>
      ))}
    </div>
  );
}

const MLB_TABS = [
  { to: "/mlb", icon: LayoutDashboard, label: "MLB" },
  { to: "/pricing", icon: CreditCard, label: "Plans" },
];

const NFL_TABS = [
  { to: "/dashboard", icon: LayoutDashboard, label: "Home" },
  { to: "/projections", icon: BarChart3, label: "Projections" },
  { to: "/simulator", icon: Cpu, label: "Sims" },
  { to: "/lineups", icon: ListOrdered, label: "Lineups" },
  { to: "/pricing", icon: CreditCard, label: "Plans" },
];

function NavLinks({ user, logout, onClick, sport }) {
  const location = useLocation();

  const linkClass = (path) =>
    `transition-colors flex items-center gap-1.5 text-sm ${
      location.pathname === path
        ? "text-venom"
        : "text-text-secondary hover:text-venom"
    }`;

  return (
    <>
      {sport === "mlb" ? (
        <>
          <Link to="/mlb" onClick={onClick} className={linkClass("/mlb")}>
            <LayoutDashboard className="w-4 h-4" /> MLB Dashboard
          </Link>
        </>
      ) : (
        <>
          <Link to="/dashboard" onClick={onClick} className={linkClass("/dashboard")}>
            <LayoutDashboard className="w-4 h-4" /> Dashboard
          </Link>
          <Link to="/projections" onClick={onClick} className={linkClass("/projections")}>
            <BarChart3 className="w-4 h-4" /> Projections
          </Link>
          <Link to="/simulator" onClick={onClick} className={linkClass("/simulator")}>
            <Cpu className="w-4 h-4" /> Simulator
          </Link>
          <Link to="/lineups" onClick={onClick} className={linkClass("/lineups")}>
            <ListOrdered className="w-4 h-4" /> Lineups
          </Link>
        </>
      )}
      <Link to="/pricing" onClick={onClick} className={linkClass("/pricing")}>
        <CreditCard className="w-4 h-4" /> Pricing
      </Link>
      <span className={TIER_STYLES[user?.tier] || TIER_STYLES.free}>
        {(user?.tier || "free").toUpperCase()}
      </span>
      <button
        onClick={() => { logout(); onClick?.(); }}
        className="text-text-muted hover:text-fangs transition-colors flex items-center gap-1.5 text-sm"
      >
        <LogOut className="w-4 h-4" /> Logout
      </button>
    </>
  );
}

function MobileTabBar({ sport }) {
  const location = useLocation();
  const tabs = sport === "mlb" ? MLB_TABS : NFL_TABS;

  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 z-50 bg-primary/95 backdrop-blur-md border-t border-border">
      <div className="flex justify-around py-2">
        {tabs.map(({ to, icon: Icon, label }) => {
          const active = location.pathname === to;
          return (
            <Link
              key={to}
              to={to}
              className={`flex flex-col items-center gap-0.5 px-3 py-1 text-xs transition-colors ${
                active ? "text-venom" : "text-text-muted"
              }`}
            >
              <Icon className="w-5 h-5" />
              {label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}

export default function Layout() {
  const { user, logout } = useAuth();
  const { sport } = useSport();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="min-h-screen flex flex-col bg-grid">
      <header className="border-b border-border bg-primary/80 backdrop-blur-md sticky top-0 z-50">
        <nav className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/" className="flex items-center gap-2.5">
              <Logo size={32} />
              <TextLogo className="text-lg" />
            </Link>
            {user && <SportSwitcher />}
          </div>

          {/* Desktop nav */}
          <div className="hidden md:flex items-center gap-6">
            {user ? (
              <NavLinks user={user} logout={logout} sport={sport} />
            ) : (
              <>
                <Link to="/login" className="text-text-secondary hover:text-venom transition-colors text-sm">
                  Login
                </Link>
                <Link to="/register" className="btn-primary btn-sm">
                  Get Started
                </Link>
              </>
            )}
          </div>

          {/* Mobile hamburger */}
          <button
            className="md:hidden text-text-secondary hover:text-venom"
            onClick={() => setMobileOpen(!mobileOpen)}
          >
            {mobileOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </nav>

        {/* Mobile nav dropdown */}
        {mobileOpen && (
          <div className="md:hidden border-t border-border bg-primary/95 backdrop-blur-md px-4 pb-4 pt-2 space-y-3 flex flex-col animate-fade-in">
            {user ? (
              <>
                <div className="pb-2">
                  <SportSwitcher />
                </div>
                <NavLinks user={user} logout={logout} onClick={() => setMobileOpen(false)} sport={sport} />
              </>
            ) : (
              <>
                <Link to="/login" onClick={() => setMobileOpen(false)} className="text-text-secondary hover:text-venom transition-colors">
                  Login
                </Link>
                <Link to="/register" onClick={() => setMobileOpen(false)} className="btn-primary btn-sm text-center">
                  Get Started
                </Link>
              </>
            )}
          </div>
        )}
      </header>

      <main className="flex-1 pb-20 md:pb-0">
        <Outlet />
      </main>

      {/* Mobile bottom tab bar */}
      {user && <MobileTabBar sport={sport} />}

      {/* Desktop footer */}
      <footer className="border-t border-border py-8 mt-auto hidden md:block">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <Logo size={20} />
              <TextLogo className="text-sm" />
            </div>
            <div className="flex gap-6 text-sm text-text-muted">
              <Link to="/pricing" className="hover:text-venom transition-colors">Pricing</Link>
              <Link to="/" className="hover:text-venom transition-colors">Home</Link>
            </div>
          </div>
          <div className="mt-4 pt-4 border-t border-border/50 text-center">
            <p className="text-xs text-text-muted">
              &copy; {new Date().getFullYear()} Stack Sniper DFS. All rights reserved.
            </p>
            <p className="mt-1 text-xs text-text-muted/60">
              Not gambling advice; for entertainment and research purposes only. Please play responsibly.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
