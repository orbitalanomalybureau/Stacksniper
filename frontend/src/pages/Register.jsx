import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import Logo, { TextLogo } from "../components/Logo";

export default function Register() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState("");
  const { register, loading } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    const success = await register(email, password, displayName);
    if (success) {
      navigate("/dashboard");
    } else {
      setError("Registration failed. Email may already be in use.");
    }
  };

  return (
    <div className="max-w-md mx-auto px-4 py-16">
      <div className="flex flex-col items-center mb-8">
        <Logo size={80} glow />
        <TextLogo className="text-2xl mt-4" />
      </div>

      <h1 className="text-2xl font-bold text-center mb-6">Create Account</h1>

      <form onSubmit={handleSubmit} className="card space-y-4">
        {error && (
          <div className="bg-fangs/10 border border-fangs/30 text-fangs rounded-lg px-4 py-2 text-sm">
            {error}
          </div>
        )}
        <div>
          <label className="block text-sm text-text-muted mb-1">Display Name</label>
          <input
            type="text"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            className="input w-full"
          />
        </div>
        <div>
          <label className="block text-sm text-text-muted mb-1">Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="input w-full"
            required
          />
        </div>
        <div>
          <label className="block text-sm text-text-muted mb-1">Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="input w-full"
            required
            minLength={8}
          />
        </div>
        <p className="text-xs text-text-muted/60">
          By signing up you acknowledge: Not gambling advice; for entertainment only.
        </p>
        <button type="submit" className="btn-primary w-full" disabled={loading}>
          {loading ? "Creating account..." : "Create Account"}
        </button>
        <p className="text-center text-sm text-text-muted">
          Already have an account?{" "}
          <Link to="/login" className="text-venom hover:underline">
            Sign in
          </Link>
        </p>
      </form>
    </div>
  );
}
