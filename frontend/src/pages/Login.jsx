import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { Moon, Sun } from "lucide-react";
import { useAuth } from "../auth.jsx";
import { useTheme } from "../theme.jsx";
import { errorMessage } from "../api.js";

const INPUT =
  "w-full rounded-lg border border-line bg-bg px-3 py-2 text-fg outline-none focus:border-accent";

export default function Login() {
  const { user, login } = useAuth();
  const { theme, toggle } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const dest = location.state?.from?.pathname || "/";

  if (user) return <Navigate to={dest} replace />;

  async function onSubmit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await login(email.trim(), password);
      navigate(dest, { replace: true });
    } catch (err) {
      setError(errorMessage(err, "Sign-in failed"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="relative grid min-h-screen place-items-center bg-bg p-4">
      <button
        type="button"
        onClick={toggle}
        aria-label="Toggle light and dark theme"
        className="absolute right-4 top-4 rounded-lg border border-line p-2 text-muted hover:text-fg"
      >
        {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
      </button>

      <div className="w-full max-w-sm">
        <div className="mb-6 text-center">
          <div className="font-display text-4xl font-bold tracking-wide">HELMEYE</div>
          <div className="text-xs tracking-widest text-muted">TRAFFIC COMMAND CENTER</div>
        </div>

        <form onSubmit={onSubmit} className="space-y-4 rounded-xl border border-line bg-surface p-6">
          <h1 className="font-display text-2xl font-bold uppercase tracking-wide">Operator sign-in</h1>

          <label className="block text-sm">
            <span className="mb-1 block text-muted">Email</span>
            <input
              type="email"
              required
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className={INPUT}
            />
          </label>

          <label className="block text-sm">
            <span className="mb-1 block text-muted">Password</span>
            <input
              type="password"
              required
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={INPUT}
            />
          </label>

          {error && (
            <p role="alert" className="text-sm text-danger">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={busy}
            className="w-full rounded-lg bg-accent px-4 py-2 font-semibold text-accent-fg disabled:opacity-60"
          >
            {busy ? "Signing in..." : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
