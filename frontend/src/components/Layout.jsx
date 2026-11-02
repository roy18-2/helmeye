import { NavLink, Outlet } from "react-router-dom";
import { Activity, LayoutDashboard, LogOut, Moon, ShieldAlert, Sun, Upload, Video } from "lucide-react";
import { useAuth } from "../auth.jsx";
import { useTheme } from "../theme.jsx";

const NAV = [
  { to: "/", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/incidents", label: "Incidents", icon: ShieldAlert },
  { to: "/upload", label: "Video Upload", icon: Upload },
  { to: "/replay", label: "Replay", icon: Video },
  { to: "/analytics", label: "Analytics", icon: Activity },
];

function navClass({ isActive }) {
  return [
    "flex items-center gap-3 whitespace-nowrap rounded-lg px-3 py-2 text-sm font-medium transition-colors",
    isActive ? "bg-accent/15 text-accent" : "text-muted hover:bg-surface2 hover:text-fg",
  ].join(" ");
}

export default function Layout() {
  const { user, logout } = useAuth();
  const { theme, toggle } = useTheme();

  return (
    <div className="min-h-screen md:flex">
      <aside className="hidden border-r border-line bg-surface md:flex md:w-60 md:shrink-0 md:flex-col">
        <div className="border-b border-line px-5 py-5">
          <div className="font-display text-2xl font-bold tracking-wide">HELMEYE</div>
          <div className="text-xs tracking-widest text-muted">TRAFFIC COMMAND</div>
        </div>
        <nav className="flex-1 space-y-1 p-3">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink key={to} to={to} end={end} className={navClass}>
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between gap-3 border-b border-line bg-surface px-4 py-3">
          <div className="font-display text-xl font-bold md:hidden">HELMEYE</div>
          <div className="hidden md:block" />
          <div className="flex items-center gap-3">
            <div className="text-right leading-tight">
              <div className="text-sm font-medium">{user?.name}</div>
              <div className="text-xs uppercase tracking-wider text-muted">{user?.role}</div>
            </div>
            <button
              type="button"
              onClick={toggle}
              aria-label="Toggle light and dark theme"
              className="rounded-lg border border-line p-2 text-muted hover:text-fg"
            >
              {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
            </button>
            <button
              type="button"
              onClick={logout}
              aria-label="Sign out"
              className="rounded-lg border border-line p-2 text-muted hover:text-fg"
            >
              <LogOut size={18} />
            </button>
          </div>
        </header>

        <nav className="flex gap-1 overflow-x-auto border-b border-line bg-surface p-2 md:hidden">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink key={to} to={to} end={end} className={navClass}>
              <Icon size={16} />
              {label}
            </NavLink>
          ))}
        </nav>

        <main className="flex-1 p-4 md:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
