import { useState } from "react";
import type { FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { apiErrorMessage } from "../components/ResourcePage";
import { Feedback } from "../components/States";

export function LoginPage() {
  const { isAuthenticated, login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();
  const location = useLocation();
  const destination =
    (location.state as { from?: string } | null)?.from ?? "/dashboard";

  if (isAuthenticated) return <Navigate to="/dashboard" replace />;

  async function submitCredentials(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(username.trim(), password);
      navigate(destination, { replace: true });
    } catch (cause) {
      setError(apiErrorMessage(cause));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="login-shell">
      <section className="login-brand">
        <div className="login-brand__content">
          <span className="eyebrow">Sistema SIPeIP</span>
          <h1>Planificación pública con trazabilidad y control.</h1>
          <p>
            Gestione planes, metas, indicadores, alineación y proyectos de
            manera sencilla y eficiente.
          </p>
          <div className="login-brand__line" />
          <span>Sistema de Planificación</span>
        </div>
      </section>
      <section className="login-panel">
        <div className="login-card">
          <div className="login-card__brand">
            <span className="brand__seal">S</span>
            <div>
              <strong>SIPeIP</strong>
              <span>Acceso institucional</span>
            </div>
          </div>
          <h2>Iniciar sesión</h2>
          <p>Ingrese sus credenciales institucionales para continuar.</p>
          <form onSubmit={submitCredentials}>
            <label>
              <span>Usuario</span>
              <input
                autoFocus
                autoComplete="username"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                required
              />
            </label>
            <label>
              <span>Contraseña</span>
              <input
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
            </label>
            <Feedback message={error} tone="error" />
            <button
              className="button button--primary button--full"
              type="submit"
              disabled={busy}
            >
              {busy ? "Verificando…" : "Ingresar"}
            </button>
          </form>
          <p className="login-card__support">
            Las operaciones quedan registradas para fines de seguridad.
          </p>
        </div>
      </section>
    </main>
  );
}
