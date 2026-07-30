from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.core.management.utils import get_random_string
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import SimpleTestCase, TestCase, TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.configuracion.models import EntidadInstitucional
from apps.metas.models import Indicador, Meta
from apps.metas.services import (
    calcular_progreso_indicador,
    calcular_seguimiento_indicador,
)
from apps.objetivos.models import ObjetivoEstrategico
from apps.planes.models import Plan
from apps.roles.models import Rol


class SeguimientoIndicadorTests(SimpleTestCase):
    """Comprueba cálculos sin depender de persistencia ni de la fecha del sistema."""

    @staticmethod
    def _indicador(**valores):
        hoy = timezone.localdate()
        predeterminados = {
            "meta": SimpleNamespace(
                fecha_inicio=hoy - timedelta(days=30),
                fecha_fin=hoy + timedelta(days=30),
            ),
            "valor_base": Decimal("0.00"),
            "valor_meta": Decimal("100.00"),
            "valor_actual": Decimal("0.00"),
            "sentido": "ASCENDENTE",
            "frecuencia": "MENSUAL",
            "validado": True,
            "avances": [],
        }
        predeterminados.update(valores)
        return SimpleNamespace(**predeterminados)

    def test_indicador_descendente_calcula_el_progreso_en_su_sentido(self):
        indicador = self._indicador(
            valor_base=Decimal("100.00"),
            valor_meta=Decimal("20.00"),
            valor_actual=Decimal("60.00"),
            sentido="DESCENDENTE",
        )

        self.assertEqual(
            calcular_progreso_indicador(indicador),
            Decimal("50.00"),
        )

    def test_indicador_no_validado_sigue_pendiente_aunque_alcance_la_meta(self):
        indicador = self._indicador(
            valor_actual=Decimal("100.00"),
            validado=False,
        )

        seguimiento = calcular_seguimiento_indicador(indicador)

        self.assertEqual(seguimiento["progreso"], Decimal("100.00"))
        self.assertEqual(
            seguimiento["estado_seguimiento"],
            "PENDIENTE_VALIDACION",
        )


class CierreMetaTests(TestCase):
    """Cubre el cierre por cumplimiento y por vencimiento del periodo."""

    @classmethod
    def setUpTestData(cls):
        hoy = timezone.localdate()
        cls.entidad = EntidadInstitucional.objects.create(
            codigo_oficial="CIERRE-TEST",
            nombre="Entidad para cierre de metas",
            subsector="Planificación",
            nivel_gobierno="Nacional",
        )
        cls.rol = Rol.objects.create(
            nombre="Gestor de cierre de metas",
            alcance=Rol.Alcance.PROPIO_ASIGNADO,
            permisos=["metas.ver", "metas.editar"],
        )
        cls.usuario = get_user_model().objects.create_user(
            username="gestor_cierre_metas",
            password=get_random_string(32),
            rol=cls.rol,
            entidad=cls.entidad,
        )
        cls.objetivo = ObjetivoEstrategico.objects.create(
            entidad=cls.entidad,
            codigo="OE-CIERRE",
            nombre="Objetivo para cierre de metas",
        )
        cls.plan = Plan.objects.create(
            nombre="Plan aprobado para cierre",
            descripcion="Plan aislado para probar cierres de seguimiento.",
            periodo_inicio=hoy - timedelta(days=365),
            periodo_fin=hoy + timedelta(days=365),
            estado=Plan.EstadoPlan.APROBADO,
            responsable=cls.usuario,
            entidad=cls.entidad,
            creado_por=cls.usuario,
        )

    def _crear_meta(self, nombre, fecha_fin, valor_actual):
        meta = Meta.objects.create(
            plan=self.plan,
            objetivo_estrategico=self.objetivo,
            nombre=nombre,
            fecha_inicio=timezone.localdate() - timedelta(days=60),
            fecha_fin=fecha_fin,
            estado=Meta.EstadoMeta.ACTIVA,
            activa=True,
        )
        Indicador.objects.create(
            meta=meta,
            nombre=f"Indicador de {nombre}",
            unidad_medida="Porcentaje",
            valor_base=Decimal("0.00"),
            valor_meta=Decimal("100.00"),
            valor_actual=valor_actual,
            sentido=Indicador.SentidoMedicion.ASCENDENTE,
            ponderacion=Decimal("100.00"),
            validado=True,
            validado_por=self.usuario,
            fecha_validacion=timezone.now(),
        )
        return meta

    def test_meta_vencida_puede_cerrarse_y_queda_incumplida(self):
        meta = self._crear_meta(
            "Meta vencida",
            timezone.localdate() - timedelta(days=1),
            Decimal("60.00"),
        )
        client = APIClient()
        client.force_authenticate(user=self.usuario)

        cierre = client.post(f"/api/metas/{meta.pk}/cerrar/", {}, format="json")

        self.assertEqual(cierre.status_code, 200)
        meta.refresh_from_db()
        self.assertEqual(meta.estado, Meta.EstadoMeta.CERRADA)
        self.assertFalse(meta.activa)

        seguimiento = client.get(f"/api/metas/{meta.pk}/seguimiento/")
        self.assertEqual(seguimiento.status_code, 200)
        self.assertEqual(
            seguimiento.data["estado_seguimiento"],
            "INCUMPLIDO",
        )

    def test_meta_no_vencida_e_incompleta_no_puede_cerrarse(self):
        meta = self._crear_meta(
            "Meta vigente incompleta",
            timezone.localdate() + timedelta(days=1),
            Decimal("60.00"),
        )
        client = APIClient()
        client.force_authenticate(user=self.usuario)

        cierre = client.post(f"/api/metas/{meta.pk}/cerrar/", {}, format="json")

        self.assertEqual(cierre.status_code, 409)
        self.assertEqual(cierre.data["code"], "meta_no_cumplida")
        self.assertIn("Antes de su vencimiento", cierre.data["detail"])
        meta.refresh_from_db()
        self.assertEqual(meta.estado, Meta.EstadoMeta.ACTIVA)
        self.assertTrue(meta.activa)

    def test_meta_cumplida_puede_cerrarse_antes_de_vencer(self):
        meta = self._crear_meta(
            "Meta vigente cumplida",
            timezone.localdate() + timedelta(days=1),
            Decimal("100.00"),
        )
        client = APIClient()
        client.force_authenticate(user=self.usuario)

        cierre = client.post(f"/api/metas/{meta.pk}/cerrar/", {}, format="json")

        self.assertEqual(cierre.status_code, 200)
        meta.refresh_from_db()
        self.assertEqual(meta.estado, Meta.EstadoMeta.CERRADA)


class MigracionSeguimientoMetasTests(TransactionTestCase):
    """Ejecuta 0005 sobre datos que representan el esquema histórico real."""

    migrate_from = (
        "metas",
        "0004_exigir_objetivo_estrategico",
    )

    def setUp(self):
        super().setUp()
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        apps = executor.loader.project_state([self.migrate_from]).apps

        Entidad = apps.get_model("configuracion", "EntidadInstitucional")
        Objetivo = apps.get_model("objetivos", "ObjetivoEstrategico")
        PlanHistorico = apps.get_model("planes", "Plan")
        MetaHistorica = apps.get_model("metas", "Meta")
        IndicadorHistorico = apps.get_model("metas", "Indicador")
        AvanceHistorico = apps.get_model("metas", "AvanceIndicador")

        entidad = Entidad.objects.create(
            codigo_oficial="MIG-LEGACY",
            nombre="Entidad histórica de migración",
            subsector="Planificación",
            nivel_gobierno="Nacional",
        )
        objetivo = Objetivo.objects.create(
            entidad_id=entidad.pk,
            codigo="OE-MIG",
            nombre="Objetivo histórico",
        )
        plan = PlanHistorico.objects.create(
            nombre="Plan histórico de migración",
            periodo_inicio="2025-01-01",
            periodo_fin="2025-12-31",
            entidad_id=entidad.pk,
        )
        meta = MetaHistorica.objects.create(
            plan_id=plan.pk,
            objetivo_estrategico_id=objetivo.pk,
            nombre="Meta histórica de migración",
            fecha_inicio="2025-01-01",
            fecha_fin="2025-12-31",
            estado="ACTIVA",
            activa=True,
        )
        self.ascendente_id = IndicadorHistorico.objects.create(
            meta_id=meta.pk,
            nombre="Indicador histórico ascendente",
            unidad_medida="Porcentaje",
            valor_base=Decimal("10.00"),
            valor_meta=Decimal("80.00"),
            valor_actual=Decimal("30.00"),
        ).pk
        self.descendente_id = IndicadorHistorico.objects.create(
            meta_id=meta.pk,
            nombre="Indicador histórico descendente",
            unidad_medida="Días",
            valor_base=Decimal("100.00"),
            valor_meta=Decimal("20.00"),
            valor_actual=Decimal("70.00"),
        ).pk
        self.igual_id = IndicadorHistorico.objects.create(
            meta_id=meta.pk,
            nombre="Indicador histórico sin variación",
            unidad_medida="Unidades",
            valor_base=Decimal("50.00"),
            valor_meta=Decimal("50.00"),
            valor_actual=Decimal("50.00"),
        ).pk
        AvanceHistorico.objects.create(
            indicador_id=self.descendente_id,
            fecha_registro="2025-06-30",
            valor=Decimal("80.00"),
            observacion="Primer registro histórico.",
        )
        AvanceHistorico.objects.create(
            indicador_id=self.descendente_id,
            fecha_registro="2025-06-30",
            valor=Decimal("70.00"),
            observacion="Corrección histórica del mismo corte.",
        )

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_0005_infiere_sentido_y_conserva_duplicados_historicos(self):
        executor = MigrationExecutor(connection)
        destinos = executor.loader.graph.leaf_nodes()
        executor.migrate(destinos)
        apps = executor.loader.project_state(destinos).apps
        IndicadorMigrado = apps.get_model("metas", "Indicador")
        AvanceMigrado = apps.get_model("metas", "AvanceIndicador")

        ascendente = IndicadorMigrado.objects.get(pk=self.ascendente_id)
        descendente = IndicadorMigrado.objects.get(pk=self.descendente_id)
        igual = IndicadorMigrado.objects.get(pk=self.igual_id)

        self.assertEqual(ascendente.sentido, "ASCENDENTE")
        self.assertEqual(descendente.sentido, "DESCENDENTE")
        self.assertEqual(igual.sentido, "ASCENDENTE")
        self.assertEqual(igual.valor_base, Decimal("50.00"))
        self.assertEqual(igual.valor_meta, Decimal("50.00"))
        self.assertEqual(
            AvanceMigrado.objects.filter(
                indicador_id=self.descendente_id,
                fecha_registro="2025-06-30",
            ).count(),
            2,
        )
