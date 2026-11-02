import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../auth.jsx";

export default function ProtectedRoute() {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return <div className="grid min-h-screen place-items-center text-muted">Loading...</div>;
  }
  if (!user) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }
  return <Outlet />;
}
