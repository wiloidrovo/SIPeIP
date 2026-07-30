"""Prueba funcional reproducible del ciclo institucional de planificación.

La prueba usa la API pública con autenticación de sesión y comprobación CSRF
real. Los catálogos y las identidades se preparan como precondiciones; todos
los registros del flujo de negocio se crean y cambian mediante endpoints.
"""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.utils import get_random_string
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.configuracion.models import EntidadInstitucional
from apps.objetivos.models import EjePND, EstadoCatalogo, ObjetivoPND, ODS
from apps.roles.models import Rol


class FlujoPlanificacionFuncionalTests(TestCase):
    """Valida un único expediente desde el borrador hasta el seguimiento."""

    @classmethod
    def setUpTestData(cls):
        cls.entidad_planificadora = EntidadInstitucional.objects.create(
            codigo_oficial="FUNC-MDI",
            nombre="Entidad funcional planificadora",
            subsector="Administración pública",
            nivel_gobierno="Nacional",
        )
        cls.entidad_supervisora = EntidadInstitucional.objects.create(
            codigo_oficial="FUNC-SNP",
            nombre="Entidad funcional supervisora",
            subsector="Planificación nacional",
            nivel_gobierno="Nacional",
        )
        cls.entidad_aislada = EntidadInstitucional.objects.create(
            codigo_oficial="FUNC-OTRA",
            nombre="Entidad funcional aislada",
            subsector="Servicios públicos",
            nivel_gobierno="Nacional",
        )

        cls.rol_planificador = Rol.objects.create(
            nombre="Planificador funcional",
            alcance=Rol.Alcance.PROPIO_ASIGNADO,
            permisos=[
                "configuracion.ver",
                "planes.ver",
                "planes.crear",
                "planes.editar",
                "planes.enviar_revision",
                "metas.ver",
                "metas.crear",
                "metas.editar",
                "indicadores.ver",
                "indicadores.crear",
                "indicadores.editar",
                "indicadores.registrar_avance",
                "objetivos.ver",
                "objetivos.gestionar",
                "alineaciones.ver",
                "alineaciones.gestionar",
            ],
        )
        cls.rol_supervisor = Rol.objects.create(
            nombre="Supervisor funcional",
            alcance=Rol.Alcance.REVISION_ENTIDAD,
            permisos=[
                "configuracion.ver",
                "planes.ver",
                "planes.revisar",
                "planes.devolver",
                "planes.aprobar",
                "planes.rechazar",
                "metas.ver",
                "indicadores.ver",
                "indicadores.validar",
                "objetivos.ver",
                "alineaciones.ver",
                "alineaciones.validar",
            ],
        )
        cls.rol_lector_aislado = Rol.objects.create(
            nombre="Lector funcional aislado",
            alcance=Rol.Alcance.LECTURA_ENTIDAD,
            permisos=[
                "planes.ver",
                "metas.ver",
                "indicadores.ver",
                "objetivos.ver",
                "alineaciones.ver",
            ],
        )

        cls.password = get_random_string(32)
        usuario_model = get_user_model()
        cls.planificador = usuario_model.objects.create_user(
            username="func_planificador",
            password=cls.password,
            rol=cls.rol_planificador,
            entidad=cls.entidad_planificadora,
        )
        cls.supervisor = usuario_model.objects.create_user(
            username="func_supervisor",
            password=cls.password,
            rol=cls.rol_supervisor,
            entidad=cls.entidad_supervisora,
        )
        cls.otro_supervisor = usuario_model.objects.create_user(
            username="func_otro_supervisor",
            password=cls.password,
            rol=cls.rol_supervisor,
            entidad=cls.entidad_supervisora,
        )
        cls.lector_aislado = usuario_model.objects.create_user(
            username="func_lector_aislado",
            password=cls.password,
            rol=cls.rol_lector_aislado,
            entidad=cls.entidad_aislada,
        )

        cls.eje_pnd = EjePND.objects.create(
            codigo="FUNC-EJE-01",
            nombre="Eje funcional",
            descripcion="Catálogo aislado para la prueba funcional.",
            estado=EstadoCatalogo.ACTIVO,
        )
        cls.objetivo_pnd = ObjetivoPND.objects.create(
            eje=cls.eje_pnd,
            codigo="FUNC-PND-01",
            nombre="Objetivo PND funcional",
            descripcion="Objetivo nacional aislado para la prueba.",
            estado=EstadoCatalogo.ACTIVO,
        )
        cls.ods = ODS.objects.create(
            numero=16,
            nombre="Instituciones sólidas para la prueba funcional",
            descripcion="Registro aislado, no presentado como catálogo oficial.",
            estado=EstadoCatalogo.ACTIVO,
        )

    def _iniciar_sesion(self, usuario):
        """Inicia una sesión como lo hace un cliente real y devuelve su CSRF."""

        client = APIClient(enforce_csrf_checks=True)
        preparacion = client.get("/api/auth/csrf/")
        self.assertEqual(preparacion.status_code, 200)
        token_inicial = preparacion.data["csrf_token"]

        login = client.post(
            "/api/auth/login/",
            {"username": usuario.username, "password": self.password},
            format="json",
            HTTP_X_CSRFTOKEN=token_inicial,
        )
        self.assertEqual(login.status_code, 200)
        self.assertEqual(login.data["usuario"]["id"], usuario.pk)
        self.assertIn("sessionid", client.cookies)

        # Django rota el secreto CSRF al autenticar.
        preparacion_posterior = client.get("/api/auth/csrf/")
        self.assertEqual(preparacion_posterior.status_code, 200)
        return client, preparacion_posterior.data["csrf_token"]

    @staticmethod
    def _post(client, token, url, data=None):
        return client.post(
            url,
            data or {},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )

    @classmethod
    def _contiene_par(cls, value, key, expected):
        """Busca un dato en estructuras anidadas sin acoplarse a la presentación."""

        if isinstance(value, dict):
            if key in value and value[key] == expected:
                return True
            return any(
                cls._contiene_par(nested, key, expected)
                for nested in value.values()
            )
        if isinstance(value, (list, tuple)):
            return any(cls._contiene_par(item, key, expected) for item in value)
        return False

    def test_plan_alineado_se_revisa_aprueba_y_actualiza_su_seguimiento(self):
        hoy = timezone.localdate()
        inicio = hoy - timedelta(days=30)
        fin = hoy + timedelta(days=335)
        descripcion_plan = (
            "Expediente funcional con contenido suficiente para que el "
            "supervisor tome una decisión informada."
        )

        # 401: ningún expediente se expone sin una sesión válida.
        sin_sesion = APIClient().get("/api/planes/1/expediente/")
        self.assertEqual(sin_sesion.status_code, 401)

        planificador, csrf_planificador = self._iniciar_sesion(self.planificador)
        plan_response = self._post(
            planificador,
            csrf_planificador,
            "/api/planes/",
            {
                "nombre": "Plan funcional integral",
                "descripcion": descripcion_plan,
                "entidad": self.entidad_planificadora.pk,
                "periodo_inicio": inicio.isoformat(),
                "periodo_fin": fin.isoformat(),
                "responsable": self.planificador.pk,
            },
        )
        self.assertEqual(plan_response.status_code, 201)
        plan_id = plan_response.data["id"]

        # Un plan sin cadena estratégica no puede presentarse como completo.
        envio_incompleto = self._post(
            planificador,
            csrf_planificador,
            f"/api/planes/{plan_id}/enviar-a-revision/",
            {"observacion": "Intento con expediente incompleto."},
        )
        self.assertEqual(envio_incompleto.status_code, 409)

        expediente_incompleto = planificador.get(
            f"/api/planes/{plan_id}/expediente/"
        )
        self.assertEqual(expediente_incompleto.status_code, 200)
        self.assertFalse(
            expediente_incompleto.data["validacion"]["listo_para_revision"]
        )
        self.assertTrue(expediente_incompleto.data["validacion"]["bloqueos"])

        objetivo_response = self._post(
            planificador,
            csrf_planificador,
            "/api/objetivos-estrategicos/",
            {
                "entidad": self.entidad_planificadora.pk,
                "codigo": "FUNC-OEI-01",
                "nombre": "Fortalecer la gestión funcional",
                "descripcion": "Objetivo creado dentro del mismo flujo de API.",
            },
        )
        self.assertEqual(objetivo_response.status_code, 201)
        objetivo_id = objetivo_response.data["id"]

        alineacion_response = self._post(
            planificador,
            csrf_planificador,
            "/api/alineaciones/",
            {
                "objetivo_estrategico": objetivo_id,
                "objetivo_pnd": self.objetivo_pnd.pk,
                "ods": self.ods.pk,
                "justificacion": (
                    "El objetivo institucional contribuye al objetivo PND "
                    "y al ODS seleccionados."
                ),
            },
        )
        self.assertEqual(alineacion_response.status_code, 201)
        alineacion_id = alineacion_response.data["id"]

        meta_response = self._post(
            planificador,
            csrf_planificador,
            "/api/metas/",
            {
                "plan": plan_id,
                "objetivo_estrategico": objetivo_id,
                "nombre": "Meta funcional verificable",
                "descripcion": "Meta asociada al objetivo y al plan funcional.",
                "resultado_esperado": "Alcanzar el valor objetivo durante el periodo.",
                "fecha_inicio": inicio.isoformat(),
                "fecha_fin": fin.isoformat(),
            },
        )
        self.assertEqual(meta_response.status_code, 201)
        meta_id = meta_response.data["id"]

        activacion_meta = self._post(
            planificador,
            csrf_planificador,
            f"/api/metas/{meta_id}/activar/",
        )
        self.assertEqual(activacion_meta.status_code, 200)

        indicador_response = self._post(
            planificador,
            csrf_planificador,
            "/api/indicadores/",
            {
                "meta": meta_id,
                "nombre": "Porcentaje funcional alcanzado",
                "descripcion": "Mide el cumplimiento de la meta funcional.",
                "unidad_medida": "Porcentaje",
                "valor_base": "10.00",
                "valor_meta": "100.00",
                "frecuencia": "MENSUAL",
                "sentido": "ASCENDENTE",
                "ponderacion": "100.00",
            },
        )
        self.assertEqual(indicador_response.status_code, 201)
        indicador_id = indicador_response.data["id"]

        expediente_estructurado = planificador.get(
            f"/api/planes/{plan_id}/expediente/"
        )
        self.assertEqual(expediente_estructurado.status_code, 200)
        self.assertTrue(
            expediente_estructurado.data["validacion"]["listo_para_revision"]
        )
        self.assertFalse(
            expediente_estructurado.data["validacion"]["listo_para_aprobacion"]
        )

        envio = self._post(
            planificador,
            csrf_planificador,
            f"/api/planes/{plan_id}/enviar-a-revision/",
            {"observacion": "Expediente funcional listo para revisión."},
        )
        self.assertEqual(envio.status_code, 200)
        self.assertEqual(envio.data["estado"], "EN_REVISION")

        # 403: el creador no puede apropiarse de la decisión del supervisor.
        aprobacion_sin_permiso = self._post(
            planificador,
            csrf_planificador,
            f"/api/planes/{plan_id}/aprobar/",
        )
        self.assertEqual(aprobacion_sin_permiso.status_code, 403)

        supervisor, csrf_supervisor = self._iniciar_sesion(self.supervisor)
        expediente = supervisor.get(f"/api/planes/{plan_id}/expediente/")
        self.assertEqual(expediente.status_code, 200)
        objetivos_visibles = supervisor.get("/api/objetivos-estrategicos/")
        alineaciones_visibles = supervisor.get("/api/alineaciones/")
        self.assertEqual(objetivos_visibles.status_code, 200)
        self.assertEqual(alineaciones_visibles.status_code, 200)
        self.assertIn(
            objetivo_id,
            {item["id"] for item in objetivos_visibles.data},
        )
        self.assertIn(
            alineacion_id,
            {item["id"] for item in alineaciones_visibles.data},
        )
        self.assertEqual(expediente.data["plan"]["id"], plan_id)
        self.assertEqual(
            expediente.data["plan"]["descripcion"],
            descripcion_plan,
        )
        self.assertTrue(
            self._contiene_par(
                expediente.data["objetivos"],
                "nombre",
                "Fortalecer la gestión funcional",
            )
        )
        self.assertTrue(
            self._contiene_par(
                expediente.data["objetivos"],
                "nombre",
                "Meta funcional verificable",
            )
        )
        self.assertTrue(
            self._contiene_par(
                expediente.data["objetivos"],
                "nombre",
                "Porcentaje funcional alcanzado",
            )
        )
        self.assertTrue(
            self._contiene_par(expediente.data["objetivos"], "numero", 16)
        )

        toma_revision = self._post(
            supervisor,
            csrf_supervisor,
            f"/api/planes/{plan_id}/revisar/",
            {"observacion": "Se inicia la revisión del expediente completo."},
        )
        self.assertEqual(toma_revision.status_code, 200)
        self.assertEqual(toma_revision.data["estado"], "EN_REVISION_INICIADA")

        validacion_alineacion = self._post(
            supervisor,
            csrf_supervisor,
            f"/api/alineaciones/{alineacion_id}/validar/",
        )
        self.assertEqual(validacion_alineacion.status_code, 200)
        self.assertEqual(validacion_alineacion.data["estado"], "VALIDADA")

        validacion_indicador = self._post(
            supervisor,
            csrf_supervisor,
            f"/api/indicadores/{indicador_id}/validar/",
        )
        self.assertEqual(validacion_indicador.status_code, 200)
        self.assertTrue(validacion_indicador.data["validado"])

        expediente_validado = supervisor.get(
            f"/api/planes/{plan_id}/expediente/"
        )
        self.assertEqual(expediente_validado.status_code, 200)
        self.assertTrue(
            expediente_validado.data["validacion"]["listo_para_aprobacion"]
        )

        # La toma de revisión debe impedir decisiones contradictorias de otro
        # supervisor. Se acepta la forma de denegación propia del contrato HTTP.
        otro_supervisor, csrf_otro_supervisor = self._iniciar_sesion(
            self.otro_supervisor
        )
        resolucion_ajena = self._post(
            otro_supervisor,
            csrf_otro_supervisor,
            f"/api/planes/{plan_id}/aprobar/",
        )
        self.assertIn(resolucion_ajena.status_code, {403, 404, 409})

        aprobacion = self._post(
            supervisor,
            csrf_supervisor,
            f"/api/planes/{plan_id}/aprobar/",
            {"observacion": "Contenido y validaciones conformes."},
        )
        self.assertEqual(aprobacion.status_code, 200)
        self.assertEqual(aprobacion.data["estado"], "APROBADO")
        self.assertEqual(
            supervisor.get(
                f"/api/planes/{plan_id}/expediente/"
            ).status_code,
            200,
        )

        avance = self._post(
            planificador,
            csrf_planificador,
            f"/api/indicadores/{indicador_id}/registrar-avance/",
            {
                "fecha_registro": hoy.isoformat(),
                "valor": "55.00",
                "observacion": "Primer corte del plan aprobado.",
            },
        )
        self.assertEqual(avance.status_code, 201)
        self.assertEqual(
            avance.data["registrado_por_detalle"]["username"],
            self.planificador.username,
        )

        seguimiento_indicador = planificador.get(
            f"/api/indicadores/{indicador_id}/seguimiento/"
        )
        self.assertEqual(seguimiento_indicador.status_code, 200)
        self.assertEqual(
            Decimal(str(seguimiento_indicador.data["progreso"])),
            Decimal("50.00"),
        )

        seguimiento_plan = planificador.get(
            f"/api/planes/{plan_id}/seguimiento/"
        )
        self.assertEqual(seguimiento_plan.status_code, 200)
        self.assertEqual(seguimiento_plan.data["plan"]["id"], plan_id)
        self.assertEqual(
            Decimal(str(seguimiento_plan.data["progreso"])),
            Decimal("50.00"),
        )
        self.assertTrue(seguimiento_plan.data["resumen"])
        self.assertTrue(
            self._contiene_par(
                seguimiento_plan.data["objetivos"],
                "numero",
                16,
            )
        )

        # Un usuario autenticado de otra institución no descubre el expediente.
        lector_aislado, csrf_lector = self._iniciar_sesion(self.lector_aislado)
        fuera_de_alcance = lector_aislado.get(
            f"/api/planes/{plan_id}/expediente/"
        )
        self.assertEqual(fuera_de_alcance.status_code, 404)

        # 403 se conserva para una acción cuyo permiso no posee.
        mutacion_lector = self._post(
            lector_aislado,
            csrf_lector,
            f"/api/planes/{plan_id}/aprobar/",
        )
        self.assertEqual(mutacion_lector.status_code, 403)
