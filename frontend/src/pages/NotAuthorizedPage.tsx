import { Link } from "react-router-dom";
export function NotAuthorizedPage() { return <section className="error-page"><span className="error-page__code">403</span><h1>Acceso no autorizado</h1><p>Su sesión es válida, pero no cuenta con el permiso necesario para consultar esta sección.</p><Link className="button button--primary" to="/dashboard">Volver al panel</Link></section>; }
