from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.utils import get_random_string
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.auditoria.models import EventoAuditoria
from apps.configuracion.models import EntidadInstitucional
from apps.metas.models import AvanceIndicador, Indicador, Meta
from apps.objetivos.models import (
    Alineacion,
    EjePND,
    ODS,
    ObjetivoEstrategico,
    ObjetivoPND,
)
from apps.planes.models import HistorialEstadoPlan, Plan
from apps.roles.models import Rol


class SipeipApiEssentialTests(TestCase):
    """Cobertura pequeña de los contratos de seguridad y negocio más sensibles."""

    @classmethod
    def setUpTestData(cls):
        cls.entidad_a = EntidadInstitucional.objects.create(
            codigo_oficial="TEST-A",
            nombre="Entidad aislada A",
            subsector="Planificación",
            nivel_gobierno="Nacional",
        )
        cls.entidad_b = EntidadInstitucional.objects.create(
            codigo_oficial="TEST-B",
            nombre="Entidad aislada B",
            subsector="Administración",
            nivel_gobierno="Nacional",
        )

        cls.rol_planificador = Rol.objects.create(
            nombre="Rol aislado de planificación",
            alcance=Rol.Alcance.PROPIO_ASIGNADO,
            permisos=[
                "planes.ver",
                "planes.crear",
                "planes.editar",
                "planes.eliminar",
                "planes.enviar_revision",
                "metas.ver",
                "metas.crear",
                "metas.editar",
                "metas.eliminar",
                "metas.archivar",
                "indicadores.ver",
                "indicadores.crear",
                "indicadores.editar",
                "indicadores.eliminar",
                "indicadores.registrar_avance",
                "objetivos.ver",
                "alineaciones.ver",
                "reportes.ver",
            ],
        )
        cls.rol_externo = Rol.objects.create(
            nombre="Rol aislado externo",
            alcance=Rol.Alcance.ENTIDAD,
            permisos=["planes.ver", "reportes.ver"],
        )
        cls.rol_auditor = Rol.objects.create(
            nombre="Rol aislado de auditoría",
            alcance=Rol.Alcance.LECTURA_ENTIDAD,
            permisos=["planes.ver", "auditoria.ver"],
        )
        cls.rol_supervisor = Rol.objects.create(
            nombre="Rol aislado de supervisión",
            alcance=Rol.Alcance.REVISION_ENTIDAD,
            permisos=[
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
        cls.rol_sin_permisos = Rol.objects.create(
            nombre="Rol aislado sin permisos",
            alcance=Rol.Alcance.ENTIDAD,
            permisos=[],
        )

        usuario_model = get_user_model()
        cls.login_password = get_random_string(32)
        cls.planificador = usuario_model.objects.create_user(
            username="test_planificador",
            password=cls.login_password,
            rol=cls.rol_planificador,
            entidad=cls.entidad_a,
        )
        cls.externo = usuario_model.objects.create_user(
            username="test_externo",
            password=get_random_string(32),
            rol=cls.rol_externo,
            entidad=cls.entidad_a,
        )
        cls.auditor = usuario_model.objects.create_user(
            username="test_auditor",
            password=get_random_string(32),
            rol=cls.rol_auditor,
            entidad=cls.entidad_a,
        )
        cls.supervisor = usuario_model.objects.create_user(
            username="test_supervisor",
            password=get_random_string(32),
            rol=cls.rol_supervisor,
            entidad=cls.entidad_b,
        )
        cls.otro_supervisor = usuario_model.objects.create_user(
            username="test_otro_supervisor",
            password=get_random_string(32),
            rol=cls.rol_supervisor,
            entidad=cls.entidad_b,
        )
        cls.sin_permisos = usuario_model.objects.create_user(
            username="test_sin_permisos",
            password=get_random_string(32),
            rol=cls.rol_sin_permisos,
            entidad=cls.entidad_a,
        )
        cls.otro_usuario = usuario_model.objects.create_user(
            username="test_otra_entidad",
            password=get_random_string(32),
            rol=cls.rol_externo,
            entidad=cls.entidad_b,
        )
        cls.superusuario = usuario_model.objects.create_superuser(
            username="test_superusuario",
            email="test-superusuario@example.invalid",
            password=get_random_string(32),
        )

        cls.objetivo_a = ObjetivoEstrategico.objects.create(
            entidad=cls.entidad_a,
            codigo="OE-A",
            nombre="Objetivo aislado A",
            descripcion="Objetivo creado únicamente dentro de la base de pruebas.",
        )
        cls.objetivo_b = ObjetivoEstrategico.objects.create(
            entidad=cls.entidad_b,
            codigo="OE-B",
            nombre="Objetivo aislado B",
            descripcion="Objetivo creado únicamente dentro de la base de pruebas.",
        )
        cls.eje_pnd = EjePND.objects.create(
            codigo="EJE-TEST",
            nombre="Eje aislado de prueba",
            descripcion="Catálogo exclusivo de la suite automatizada.",
        )
        cls.objetivo_pnd = ObjetivoPND.objects.create(
            eje=cls.eje_pnd,
            codigo="PND-TEST",
            nombre="Objetivo PND aislado",
            descripcion="Catálogo exclusivo de la suite automatizada.",
        )
        cls.ods = ODS.objects.create(
            numero=16,
            nombre="ODS aislado de prueba",
            descripcion="Registro exclusivo de la suite automatizada.",
        )
        cls.alineacion_a = Alineacion.objects.create(
            objetivo_estrategico=cls.objetivo_a,
            objetivo_pnd=cls.objetivo_pnd,
            ods=cls.ods,
            justificacion="Alineación exclusiva para comprobar el flujo de revisión.",
            usuario_creador=cls.planificador,
        )
        cls.plan_a = Plan.objects.create(
            nombre="Plan aislado A",
            descripcion="Registro de prueba de la entidad A.",
            periodo_inicio="2026-01-01",
            periodo_fin="2026-12-31",
            responsable=cls.planificador,
            entidad=cls.entidad_a,
            creado_por=cls.planificador,
        )
        cls.plan_b = Plan.objects.create(
            nombre="Plan aislado B",
            descripcion="Registro de prueba de la entidad B.",
            periodo_inicio="2026-01-01",
            periodo_fin="2026-12-31",
            responsable=cls.otro_usuario,
            entidad=cls.entidad_b,
            creado_por=cls.otro_usuario,
        )
        cls.plan_externo_a = Plan.objects.create(
            nombre="Plan visible del usuario externo",
            descripcion="Registro propio de prueba dentro de la entidad A.",
            periodo_inicio="2026-01-01",
            periodo_fin="2026-12-31",
            responsable=cls.externo,
            entidad=cls.entidad_a,
            creado_por=cls.externo,
        )
        cls.meta_activa = Meta.objects.create(
            plan=cls.plan_a,
            objetivo_estrategico=cls.objetivo_a,
            nombre="Meta aislada activa",
            descripcion="Meta de prueba.",
            resultado_esperado="Resultado de prueba.",
            fecha_inicio="2026-01-01",
            fecha_fin="2026-12-31",
            estado=Meta.EstadoMeta.ACTIVA,
            activa=True,
        )
        cls.indicador = Indicador.objects.create(
            meta=cls.meta_activa,
            nombre="Indicador aislado",
            descripcion="Indicador de prueba.",
            unidad_medida="Porcentaje",
            valor_base=Decimal("0.00"),
            valor_meta=Decimal("100.00"),
            valor_actual=Decimal("0.00"),
            frecuencia=Indicador.FrecuenciaMedicion.MENSUAL,
            ponderacion=Decimal("100.00"),
        )

    @staticmethod
    def _cliente_autenticado(usuario):
        client = APIClient()
        client.force_authenticate(user=usuario)
        return client

    @staticmethod
    def _token_csrf(client):
        response = client.get("/api/auth/csrf/")
        return response, response.data["csrf_token"]

    def test_csrf_prepara_token_y_cookie(self):
        client = APIClient(enforce_csrf_checks=True)

        response, token = self._token_csrf(client)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(token)
        self.assertIn("csrftoken", response.cookies)

    def test_login_exige_csrf_crea_sesion_y_logout_la_cierra(self):
        client = APIClient(enforce_csrf_checks=True)
        credenciales = {
            "username": self.planificador.username,
            "password": self.login_password,
        }

        sin_csrf = client.post("/api/auth/login/", credenciales, format="json")
        self.assertEqual(sin_csrf.status_code, 403)
        self.assertEqual(sin_csrf.json()["code"], "csrf_failed")

        _, token = self._token_csrf(client)
        login = client.post(
            "/api/auth/login/",
            credenciales,
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(login.status_code, 200)
        self.assertEqual(login.data["usuario"]["username"], self.planificador.username)
        self.assertIn("sessionid", client.cookies)
        self.assertEqual(client.get("/api/auth/me/").status_code, 200)

        # Django rota el secreto CSRF al autenticar. Se obtiene un token nuevo
        # antes de la siguiente escritura, igual que debe hacer la SPA.
        _, token = self._token_csrf(client)
        logout = client.post(
            "/api/auth/logout/",
            {},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(logout.status_code, 200)
        self.assertEqual(client.get("/api/auth/me/").status_code, 401)

    def test_login_incorrecto_devuelve_401_y_deja_auditoria_sin_clave(self):
        client = APIClient(enforce_csrf_checks=True)
        _, token = self._token_csrf(client)
        clave_incorrecta = get_random_string(32)

        response = client.post(
            "/api/auth/login/",
            {"username": self.planificador.username, "password": clave_incorrecta},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )

        self.assertEqual(response.status_code, 401)
        evento = EventoAuditoria.objects.get(accion="LOGIN", resultado="FALLO")
        self.assertEqual(evento.usuario_identificador, self.planificador.username)
        self.assertNotIn(clave_incorrecta, str(evento.valores_anteriores))
        self.assertNotIn(clave_incorrecta, str(evento.valores_posteriores))
        self.assertNotIn(clave_incorrecta, evento.detalle)

    def test_recurso_protegido_distingue_401_y_403(self):
        sin_sesion = APIClient().get("/api/planes/")
        sin_permiso = self._cliente_autenticado(self.sin_permisos).get("/api/planes/")

        self.assertEqual(sin_sesion.status_code, 401)
        self.assertEqual(sin_sesion.data["code"], "not_authenticated")
        self.assertEqual(sin_permiso.status_code, 403)
        self.assertEqual(sin_permiso.data["code"], "permission_denied")

    def test_alcance_institucional_no_lista_planes_de_otra_entidad(self):
        response = self._cliente_autenticado(self.externo).get("/api/planes/")

        self.assertEqual(response.status_code, 200)
        nombres = {plan["nombre"] for plan in response.data}
        self.assertIn(self.plan_externo_a.nombre, nombres)
        self.assertNotIn(self.plan_b.nombre, nombres)

    def test_agregados_de_alineacion_respetan_planes_visibles(self):
        meta_ajena = Meta.objects.create(
            plan=self.plan_externo_a,
            objetivo_estrategico=self.objetivo_a,
            nombre="Meta no asignada al planificador",
            descripcion="No debe contarse fuera del alcance propio.",
            resultado_esperado="Mantener aislamiento de agregados.",
            fecha_inicio="2026-01-01",
            fecha_fin="2026-12-31",
            estado=Meta.EstadoMeta.ACTIVA,
            activa=True,
        )
        Indicador.objects.create(
            meta=meta_ajena,
            nombre="Indicador no asignado",
            descripcion="No debe incluirse en agregados ajenos.",
            unidad_medida="Porcentaje",
            valor_base=Decimal("0.00"),
            valor_meta=Decimal("100.00"),
            valor_actual=Decimal("0.00"),
            ponderacion=Decimal("100.00"),
        )

        response = self._cliente_autenticado(self.planificador).get(
            f"/api/alineaciones/{self.alineacion_a.pk}/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["planes_count"], 1)
        self.assertEqual(response.data["metas_count"], 1)
        self.assertEqual(response.data["indicadores_count"], 1)
        self.assertEqual(
            {plan["id"] for plan in response.data["planes_relacionados"]},
            {self.plan_a.pk},
        )

    def test_meta_rechaza_objetivo_de_otra_entidad_y_acepta_el_coherente(self):
        client = self._cliente_autenticado(self.superusuario)
        base = {
            "plan": self.plan_a.pk,
            "nombre": "Meta creada mediante API",
            "descripcion": "Meta de validación.",
            "resultado_esperado": "Resultado verificable.",
            "fecha_inicio": "2026-02-01",
            "fecha_fin": "2026-11-30",
        }

        cruzada = client.post(
            "/api/metas/",
            {**base, "objetivo_estrategico": self.objetivo_b.pk},
            format="json",
        )
        coherente = client.post(
            "/api/metas/",
            {**base, "objetivo_estrategico": self.objetivo_a.pk},
            format="json",
        )

        self.assertEqual(cruzada.status_code, 400)
        self.assertIn("objetivo_estrategico", cruzada.data)
        self.assertEqual(coherente.status_code, 201)
        self.assertEqual(coherente.data["objetivo_estrategico"], self.objetivo_a.pk)

    def test_transicion_de_plan_es_controlada_y_repetirla_devuelve_409(self):
        client = self._cliente_autenticado(self.planificador)
        url = f"/api/planes/{self.plan_a.pk}/enviar-a-revision/"

        primera = client.post(url, {"observacion": "Listo para revisión."}, format="json")
        repetida = client.post(url, {"observacion": "Intento repetido."}, format="json")

        self.plan_a.refresh_from_db()
        self.assertEqual(primera.status_code, 200)
        self.assertEqual(self.plan_a.estado, Plan.EstadoPlan.EN_REVISION)
        self.assertEqual(repetida.status_code, 409)
        self.assertEqual(
            HistorialEstadoPlan.objects.filter(plan=self.plan_a).count(),
            1,
        )

    def test_supervisor_recibe_y_resuelve_revision_interinstitucional(self):
        planificador = self._cliente_autenticado(self.planificador)
        supervisor = self._cliente_autenticado(self.supervisor)

        envio = planificador.post(
            f"/api/planes/{self.plan_a.pk}/enviar-a-revision/",
            {"observacion": "Listo para revisión institucional."},
            format="json",
        )
        bandeja = supervisor.get("/api/planes/")

        self.assertEqual(envio.status_code, 200)
        self.assertEqual(bandeja.status_code, 200)
        ids_visibles = {plan["id"] for plan in bandeja.data}
        self.assertIn(self.plan_a.pk, ids_visibles)
        self.assertIn(self.plan_b.pk, ids_visibles)
        self.assertNotIn(self.plan_externo_a.pk, ids_visibles)

        metas = supervisor.get("/api/metas/")
        indicadores = supervisor.get("/api/indicadores/")
        self.assertIn(self.meta_activa.pk, {meta["id"] for meta in metas.data})
        self.assertIn(
            self.indicador.pk,
            {indicador["id"] for indicador in indicadores.data},
        )
        self.assertEqual(
            supervisor.patch(
                f"/api/metas/{self.meta_activa.pk}/",
                {"nombre": "Mutación no autorizada"},
                format="json",
            ).status_code,
            403,
        )

        dashboard = supervisor.get("/api/dashboard/")
        widgets = {
            widget["codigo"]: widget["valor"]
            for widget in dashboard.data["widgets"]
        }
        self.assertEqual(widgets["bandeja_revision"], 1)

        revision = supervisor.post(
            f"/api/planes/{self.plan_a.pk}/revisar/",
            {},
            format="json",
        )
        seguimiento_indicador = supervisor.get(
            f"/api/indicadores/{self.indicador.pk}/seguimiento/"
        )
        alineacion_asignada = supervisor.get(
            f"/api/alineaciones/{self.alineacion_a.pk}/"
        )
        validacion_alineacion = supervisor.post(
            f"/api/alineaciones/{self.alineacion_a.pk}/validar/",
            {},
            format="json",
        )
        validacion_indicador = supervisor.post(
            f"/api/indicadores/{self.indicador.pk}/validar/",
            {},
            format="json",
        )
        aprobacion = supervisor.post(
            f"/api/planes/{self.plan_a.pk}/aprobar/",
            {},
            format="json",
        )
        detalle_posterior = supervisor.get(
            f"/api/planes/{self.plan_a.pk}/"
        )

        self.plan_a.refresh_from_db()
        self.assertEqual(revision.status_code, 200)
        self.assertEqual(seguimiento_indicador.status_code, 200)
        self.assertEqual(
            seguimiento_indicador.data["plan"]["revisor"],
            self.supervisor.pk,
        )
        self.assertEqual(alineacion_asignada.status_code, 200)
        self.assertTrue(alineacion_asignada.data["puede_resolver"])
        self.assertEqual(validacion_alineacion.status_code, 200)
        self.assertEqual(validacion_indicador.status_code, 200)
        self.assertEqual(aprobacion.status_code, 200)
        self.assertEqual(self.plan_a.estado, Plan.EstadoPlan.APROBADO)
        self.assertEqual(detalle_posterior.status_code, 200)
        otra_bandeja = self._cliente_autenticado(self.otro_supervisor).get(
            "/api/planes/"
        )
        self.assertNotIn(
            self.plan_a.pk,
            {plan["id"] for plan in otra_bandeja.data},
        )

    def test_expediente_aprobado_inmoviliza_objetivo_y_catalogos(self):
        Plan.objects.filter(pk=self.plan_a.pk).update(
            estado=Plan.EstadoPlan.APROBADO,
        )
        client = self._cliente_autenticado(self.superusuario)

        objetivo = client.patch(
            f"/api/objetivos-estrategicos/{self.objetivo_a.pk}/",
            {"descripcion": "Intento de alterar una decisión histórica."},
            format="json",
        )
        ods = client.post(
            f"/api/ods/{self.ods.pk}/desactivar/",
            {},
            format="json",
        )
        ods_alternativo = ODS.objects.create(
            numero=17,
            nombre="ODS alternativo de prueba",
            descripcion="Catálogo auxiliar exclusivo de esta prueba.",
        )
        nueva_alineacion = client.post(
            "/api/alineaciones/",
            {
                "objetivo_estrategico": self.objetivo_a.pk,
                "objetivo_pnd": self.objetivo_pnd.pk,
                "ods": ods_alternativo.pk,
                "justificacion": (
                    "Intento de cambiar la alineación de un expediente aprobado."
                ),
            },
            format="json",
        )
        alineacion_existente = client.patch(
            f"/api/alineaciones/{self.alineacion_a.pk}/",
            {"justificacion": "Intento de alterar la alineación aprobada."},
            format="json",
        )
        entidad = client.post(
            (
                f"/api/configuracion/entidades/"
                f"{self.entidad_a.pk}/desactivar/"
            ),
            {},
            format="json",
        )

        self.assertEqual(objetivo.status_code, 409)
        self.assertEqual(objetivo.data["code"], "expediente_inmutable")
        self.assertEqual(ods.status_code, 409)
        self.assertEqual(ods.data["code"], "expediente_inmutable")
        self.assertEqual(nueva_alineacion.status_code, 409)
        self.assertEqual(
            nueva_alineacion.data["code"],
            "expediente_inmutable",
        )
        self.assertEqual(alineacion_existente.status_code, 409)
        self.assertEqual(
            alineacion_existente.data["code"],
            "expediente_inmutable",
        )
        self.assertEqual(entidad.status_code, 409)
        self.assertEqual(entidad.data["code"], "entidad_con_plan_vigente")

    def test_plan_aprobado_impide_archivar_meta_y_alterar_seguimiento(self):
        Plan.objects.filter(pk=self.plan_a.pk).update(
            estado=Plan.EstadoPlan.APROBADO,
        )
        response = self._cliente_autenticado(self.planificador).post(
            f"/api/metas/{self.meta_activa.pk}/archivar/",
            {},
            format="json",
        )

        self.meta_activa.refresh_from_db()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "plan_no_editable")
        self.assertEqual(self.meta_activa.estado, Meta.EstadoMeta.ACTIVA)
        self.assertTrue(self.meta_activa.activa)

    def test_catalogo_inactivo_bloquea_envio_del_plan(self):
        ODS.objects.filter(pk=self.ods.pk).update(estado="INACTIVO")
        response = self._cliente_autenticado(self.planificador).post(
            f"/api/planes/{self.plan_a.pk}/enviar-a-revision/",
            {"observacion": "No debe enviarse con catálogos obsoletos."},
            format="json",
        )

        self.assertEqual(response.status_code, 409)
        codigos = {
            bloqueo["codigo"]
            for bloqueo in response.data["validacion"]["bloqueos_revision"]
        }
        self.assertIn("ALINEACION_CON_CATALOGO_INACTIVO", codigos)

    def test_avance_usa_usuario_de_sesion_y_actualiza_indicador(self):
        Plan.objects.filter(pk=self.plan_a.pk).update(
            estado=Plan.EstadoPlan.APROBADO,
        )
        Indicador.objects.filter(pk=self.indicador.pk).update(
            validado=True,
            validado_por=self.supervisor,
            fecha_validacion=timezone.now(),
        )
        self.plan_a.refresh_from_db()
        self.indicador.refresh_from_db()
        client = self._cliente_autenticado(self.planificador)
        url = f"/api/indicadores/{self.indicador.pk}/registrar-avance/"

        response = client.post(
            url,
            {
                "fecha_registro": "2026-06-30",
                "valor": "37.50",
                "observacion": "Medición aislada.",
                "registrado_por": self.otro_usuario.pk,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        avance = AvanceIndicador.objects.get(pk=response.data["id"])
        self.indicador.refresh_from_db()
        self.assertEqual(avance.registrado_por, self.planificador)
        self.assertEqual(self.indicador.valor_actual, Decimal("37.50"))

    def test_eliminacion_de_meta_con_indicador_devuelve_409(self):
        response = self._cliente_autenticado(self.superusuario).delete(
            f"/api/metas/{self.meta_activa.pk}/"
        )

        self.assertEqual(response.status_code, 409)
        self.assertTrue(Meta.objects.filter(pk=self.meta_activa.pk).exists())
        self.assertTrue(Indicador.objects.filter(pk=self.indicador.pk).exists())

    def test_auditor_puede_leer_pero_no_modificar(self):
        client = self._cliente_autenticado(self.auditor)

        lectura = client.get(f"/api/planes/{self.plan_a.pk}/")
        escritura = client.patch(
            f"/api/planes/{self.plan_a.pk}/",
            {"nombre": "Cambio no permitido"},
            format="json",
        )

        self.assertEqual(lectura.status_code, 200)
        self.assertEqual(escritura.status_code, 403)

    def test_reporte_no_filtra_datos_de_otra_institucion(self):
        client = self._cliente_autenticado(self.externo)

        response = client.get("/api/reportes/generar/planes/")
        filtro_manipulado = client.get(
            f"/api/reportes/generar/planes/?entidad={self.entidad_b.pk}"
        )

        self.assertEqual(response.status_code, 200)
        nombres = {fila["nombre"] for fila in response.data["resultados"]}
        self.assertIn(self.plan_externo_a.nombre, nombres)
        self.assertNotIn(self.plan_b.nombre, nombres)
        self.assertEqual(filtro_manipulado.status_code, 200)
        self.assertEqual(filtro_manipulado.data["resultados"], [])
