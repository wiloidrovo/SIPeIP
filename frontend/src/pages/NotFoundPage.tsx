import { Link } from "react-router-dom";
export function NotFoundPage() { return <main className="error-page error-page--standalone"><span className="error-page__code">404</span><h1>Página no encontrada</h1><p>La dirección solicitada no corresponde a una ruta disponible en SIPeIP.</p><Link className="button button--primary" to="/dashboard">Ir al panel</Link></main>; }
