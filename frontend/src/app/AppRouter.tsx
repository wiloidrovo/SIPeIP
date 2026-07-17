import { Navigate, Route, Routes } from "react-router-dom";
import { ProtectedRoute } from "../auth/ProtectedRoute";
import { AppLayout } from "../layouts/AppLayout";
import { AuditoriaPage } from "../modules/auditoria/AuditoriaPage";
import { PndPage } from "../modules/alineacion/PndPage";
import { OdsPage } from "../modules/alineacion/OdsPage";
import { AvancesPage } from "../modules/avances/AvancesPage";
import { EntidadesPage } from "../modules/configuracion/EntidadesPage";
import { UnidadesPage } from "../modules/configuracion/UnidadesPage";
import { IndicadoresPage } from "../modules/indicadores/IndicadoresPage";
import { MetasPage } from "../modules/metas/MetasPage";
import { ObjetivosPage } from "../modules/objetivos/ObjetivosPage";
import { PlanesPage } from "../modules/planes/PlanesPage";
import { ProyectosPage } from "../modules/proyectos/ProyectosPage";
import { ReportesPage } from "../modules/reportes/ReportesPage";
import { RolesPage } from "../modules/roles/RolesPage";
import { UsuariosPage } from "../modules/usuarios/UsuariosPage";
import { DashboardPage } from "../pages/DashboardPage";
import { LoginPage } from "../pages/LoginPage";
import { NotAuthorizedPage } from "../pages/NotAuthorizedPage";
import { NotFoundPage } from "../pages/NotFoundPage";

function Secured({ permission, children }: { permission: string; children: React.ReactNode }) {
  return <Route element={<ProtectedRoute permissions={[permission]} />}><Route element={<AppLayout />}>{children}</Route></Route>;
}

export function AppRouter() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/no-autorizado" element={<NotAuthorizedPage />} />
        </Route>
      </Route>
      {Secured({ permission: "usuarios.ver", children: <Route path="/usuarios" element={<UsuariosPage />} /> })}
      {Secured({ permission: "roles.ver", children: <Route path="/roles" element={<RolesPage />} /> })}
      {Secured({ permission: "configuracion.ver", children: <Route path="/configuracion/entidades" element={<EntidadesPage />} /> })}
      {Secured({ permission: "configuracion.ver", children: <Route path="/configuracion/unidades" element={<UnidadesPage />} /> })}
      {Secured({ permission: "planes.ver", children: <Route path="/planes" element={<PlanesPage />} /> })}
      {Secured({ permission: "metas.ver", children: <Route path="/metas" element={<MetasPage />} /> })}
      {Secured({ permission: "indicadores.ver", children: <Route path="/indicadores" element={<IndicadoresPage />} /> })}
      {Secured({ permission: "indicadores.ver", children: <Route path="/avances" element={<AvancesPage />} /> })}
      {Secured({ permission: "objetivos.ver", children: <Route path="/objetivos" element={<ObjetivosPage />} /> })}
      {Secured({ permission: "alineaciones.ver", children: <Route path="/alineacion/pnd" element={<PndPage />} /> })}
      {Secured({ permission: "alineaciones.ver", children: <Route path="/alineacion/ods" element={<OdsPage />} /> })}
      {Secured({ permission: "proyectos.ver", children: <Route path="/proyectos" element={<ProyectosPage />} /> })}
      {Secured({ permission: "reportes.ver", children: <Route path="/reportes" element={<ReportesPage />} /> })}
      {Secured({ permission: "auditoria.ver", children: <Route path="/auditoria" element={<AuditoriaPage />} /> })}
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
