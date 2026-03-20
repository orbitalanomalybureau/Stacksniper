import { Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import Home from "./pages/Home";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import Projections from "./pages/Projections";
import Simulator from "./pages/Simulator";
import Lineups from "./pages/Lineups";
import Pricing from "./pages/Pricing";
import MLBDashboard from "./pages/MLBDashboard";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/pricing" element={<Pricing />} />

        {/* MLB routes (default sport) */}
        <Route path="/mlb" element={<ProtectedRoute><MLBDashboard /></ProtectedRoute>} />

        {/* NFL routes */}
        <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
        <Route path="/projections" element={<Projections />} />
        <Route path="/simulator" element={<ProtectedRoute><Simulator /></ProtectedRoute>} />
        <Route path="/lineups" element={<ProtectedRoute><Lineups /></ProtectedRoute>} />

        {/* Redirect /nfl to legacy dashboard */}
        <Route path="/nfl" element={<Navigate to="/dashboard" replace />} />
      </Route>
    </Routes>
  );
}
