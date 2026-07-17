import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import type { PropsWithChildren } from "react";
import { ApiError, authApi } from "../services/api";
import type { SessionResponse, SessionUser } from "./types";

type AuthContextValue = {
  user: SessionUser | null;
  loading: boolean;
  isAuthenticated: boolean;
  hasPermission: (code: string) => boolean;
  hasAllPermissions: (codes: string[]) => boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  reloadSession: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: PropsWithChildren) {
  const [user, setUser] = useState<SessionUser | null>(null);
  const [loading, setLoading] = useState(true);
  const mounted = useRef(true);
  // StrictMode repite los efectos en desarrollo; el arranque de sesión debe
  // seguir siendo una única operación de red.
  const bootstrapped = useRef(false);
  const renewing = useRef(false);

  const reloadSession = useCallback(async () => {
    try {
      const session = await authApi.me<SessionUser>();
      if (mounted.current) setUser(session);
    } catch (error) {
      if (!(error instanceof ApiError) || error.status !== 401) throw error;
      if (mounted.current) setUser(null);
    }
  }, []);

  useEffect(() => {
    mounted.current = true;
    if (!bootstrapped.current) {
      bootstrapped.current = true;
      authApi
        .csrf()
        .then(reloadSession)
        .catch(() => {
          if (mounted.current) setUser(null);
        })
        .finally(() => {
          if (mounted.current) setLoading(false);
        });
    }

    const clearSession = () => setUser(null);
    window.addEventListener("sipeip:unauthorized", clearSession);
    return () => {
      mounted.current = false;
      window.removeEventListener("sipeip:unauthorized", clearSession);
    };
  }, [reloadSession]);

  useEffect(() => {
    if (!user) return;
    const renew = async () => {
      if (renewing.current) return;
      renewing.current = true;
      try {
        const response = await authApi.refresh<SessionResponse>();
        if (mounted.current) setUser(response.usuario);
      } catch (error) {
        // Un fallo transitorio de red no equivale a una sesión expirada. El
        // siguiente request volverá a intentar la renovación de forma acotada.
        if (error instanceof ApiError && error.status === 401 && mounted.current) {
          setUser(null);
        }
      } finally {
        renewing.current = false;
      }
    };
    const interval = window.setInterval(renew, 8 * 60 * 1000);
    const onVisible = () => {
      if (document.visibilityState === "visible") void renew();
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      window.clearInterval(interval);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [user?.id]);

  const login = useCallback(async (username: string, password: string) => {
    const response = await authApi.login<SessionResponse>(username, password);
    setUser(response.usuario);
  }, []);

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } finally {
      setUser(null);
    }
  }, []);

  const permissions = useMemo(() => new Set(user?.permisos ?? []), [user]);
  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      isAuthenticated: Boolean(user),
      hasPermission: (code) => Boolean(user?.es_superusuario || permissions.has(code)),
      hasAllPermissions: (codes) =>
        Boolean(user?.es_superusuario || codes.every((code) => permissions.has(code))),
      login,
      logout,
      reloadSession,
    }),
    [user, loading, permissions, login, logout, reloadSession],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth debe utilizarse dentro de AuthProvider.");
  return context;
}
