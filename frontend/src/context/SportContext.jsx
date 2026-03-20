import { createContext, useContext, useState, useCallback } from "react";

const SportContext = createContext(null);

const SPORTS = {
  mlb: { key: "mlb", label: "MLB", emoji: "\u26be", apiPrefix: "/api/mlb" },
  nfl: { key: "nfl", label: "NFL", emoji: "\ud83c\udfc8", apiPrefix: "/api/nfl" },
};

export function SportProvider({ children }) {
  const [sport, setSportRaw] = useState(() => {
    try {
      return localStorage.getItem("stacksniper_sport") || "mlb";
    } catch {
      return "mlb";
    }
  });

  const setSport = useCallback((s) => {
    setSportRaw(s);
    try {
      localStorage.setItem("stacksniper_sport", s);
    } catch {}
  }, []);

  const sportConfig = SPORTS[sport] || SPORTS.mlb;

  return (
    <SportContext.Provider value={{ sport, setSport, sportConfig, SPORTS }}>
      {children}
    </SportContext.Provider>
  );
}

export function useSport() {
  const ctx = useContext(SportContext);
  if (!ctx) throw new Error("useSport must be used within SportProvider");
  return ctx;
}

export default SportContext;
