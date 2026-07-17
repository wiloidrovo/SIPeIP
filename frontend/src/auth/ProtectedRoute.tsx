import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "./AuthContext";
import { LoadingState } from "../components/States";

export function ProtectedRoute({ permissions = [] }: { permissions?: string[] }) {
  const { loading, isAuthenticated, hasAllPermissions } = useAuth();
  const location = useLocation();

  if (loading) return <LoadingState label="Verificando sesión" fullPage />;
  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  if (permissions.length && !hasAllPermissions(permissions)) {
    return <Navigate to="/no-autorizado" replace />;
  }
  return <Outlet />;
}
