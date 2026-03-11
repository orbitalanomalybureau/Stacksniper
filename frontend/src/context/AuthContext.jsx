import { createContext, useContext, useState, useCallback, useEffect } from "react";
import apiClient, { setAccessToken, clearAccessToken } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const restoreSession = async () => {
      try {
        const { data: refreshData } = await apiClient.post("/api/auth/refresh");
        setAccessToken(refreshData.access_token);
        const { data: meData } = await apiClient.get("/api/auth/me");
        setUser(meData);
      } catch {
        // No valid session
      } finally {
        setLoading(false);
      }
    };
    restoreSession();
  }, []);

  const fetchMe = useCallback(async () => {
    const { data } = await apiClient.get("/api/auth/me");
    setUser(data);
    return data;
  }, []);

  const login = useCallback(async (email, password) => {
    setLoading(true);
    try {
      const { data } = await apiClient.post("/api/auth/login", { email, password });
      setAccessToken(data.access_token);
      setUser(data.user);
      return true;
    } catch {
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  const register = useCallback(async (email, password, displayName) => {
    setLoading(true);
    try {
      const { data } = await apiClient.post("/api/auth/register", {
        email,
        password,
        display_name: displayName,
      });
      setAccessToken(data.access_token);
      setUser(data.user);
      return true;
    } catch {
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await apiClient.post("/api/auth/logout");
    } catch {
      // Ignore logout errors
    }
    clearAccessToken();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, fetchMe }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
