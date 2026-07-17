import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { Feedback } from "../components/States";
import { navigation } from "./navigation";

export function AppLayout() {
  const { user, hasPermission, logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [forbidden, setForbidden] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => setMobileOpen(false), [location.pathname]);
  useEffect(() => {
    const onForbidden = () => setForbidden(true);
    window.addEventListener("sipeip:forbidden", onForbidden);
    return () => window.removeEventListener("sipeip:forbidden", onForbidden);
  }, []);

  async function signOut() {
    try {
      await logout();
    } finally {
      navigate("/login", { replace: true });
    }
  }

  const visibleGroups = navigation
    .map((group) => ({
      ...group,
      items: group.items.filter(
        (item) => !item.permission || hasPermission(item.permission),
      ),
    }))
    .filter((group) => group.items.length);

  return (
    <div className={`shell${mobileOpen ? " shell--mobile-open" : ""}`}>
      <a className="skip-link" href="#main-content">
        Ir al contenido principal
      </a>
      <aside
        className="sidebar"
        id="primary-navigation"
        aria-label="Navegación principal"
      >
        <div className="brand">
          <div className="brand__seal" aria-hidden="true">
            S
          </div>
          <div className="brand__text">
            <strong>SIPeIP</strong>
            <span>Planificación institucional</span>
          </div>
        </div>
        <nav className="sidebar__nav">
          {visibleGroups.map((group) => (
            <div className="nav-group" key={group.label}>
              <span className="nav-group__label">{group.label}</span>
              {group.items.map((item) => (
                <NavLink
                  className={({ isActive }) =>
                    `nav-item${isActive ? " nav-item--active" : ""}`
                  }
                  to={item.path}
                  key={item.path}
                >
                  <span className="nav-item__mark" aria-hidden="true">
                    {item.mark}
                  </span>
                  <span className="nav-item__label">{item.label}</span>
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
        <div className="sidebar__footer">
          <button
            type="button"
            className="nav-item sidebar__logout"
            onClick={() => void signOut()}
          >
            <span className="nav-item__mark" aria-hidden="true">
              C
            </span>
            <span className="nav-item__label">Cerrar sesión</span>
          </button>
        </div>
      </aside>
      <button
        type="button"
        className="sidebar-overlay"
        aria-label="Cerrar navegación"
        onClick={() => setMobileOpen(false)}
      />
      <div className="shell__main">
        <header className="topbar">
          <div className="topbar__left">
            <button
              type="button"
              className="icon-button mobile-toggle"
              aria-label="Abrir menú"
              aria-controls="primary-navigation"
              aria-expanded={mobileOpen}
              onClick={() => setMobileOpen(true)}
            >
              <span className="menu-lines" aria-hidden="true" />
            </button>
            <div className="topbar__context">
              <span>Sistema de Planificación</span>
              <strong>
                {user?.institucion?.nombre ?? "Cobertura general"}
              </strong>
            </div>
          </div>
          <div className="user-menu">
            <div className="user-avatar" aria-hidden="true">
              {(user?.nombre_completo ?? "U").slice(0, 1).toUpperCase()}
            </div>
            <div className="user-menu__identity">
              <strong>{user?.nombre_completo}</strong>
              <span>{user?.rol?.nombre ?? "Administración"}</span>
            </div>
            <button
              type="button"
              className="button button--quiet"
              onClick={() => void signOut()}
            >
              Cerrar sesión
            </button>
          </div>
        </header>
        <main className="content" id="main-content">
          {forbidden ? (
            <Feedback
              tone="error"
              message="La sesión está activa, pero no tiene permiso para completar esa operación."
              onClose={() => setForbidden(false)}
            />
          ) : null}
          <Outlet />
        </main>
      </div>
    </div>
  );
}
