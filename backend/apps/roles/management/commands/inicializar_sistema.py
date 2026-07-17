"""Inicializa los catálogos y registros locales indispensables de SIPeIP."""

from datetime import date, datetime
from decimal import Decimal

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone

from apps.auditoria.models import EventoAuditoria
from apps.configuracion.models import EntidadInstitucional, UnidadOrganizacional
from apps.metas.models import AvanceIndicador, Indicador, Meta
from apps.objetivos.models import (
    Alineacion,
    EjePND,
    EstadoCatalogo,
    ODS,
    ObjetivoEstrategico,
    ObjetivoPND,
)
from apps.planes.models import Plan
from apps.proyectos.models import (
    HitoProyecto,
    ProyectoInversion,
    SeguimientoProyecto,
    TipologiaIntervencion,
)
from apps.roles.models import Rol
from apps.usuarios.models import Usuario


USUARIOS_INICIALES = (
    "administrador",
    "planificador",
    "supervisor",
    "externo",
    "auditor",
    "superadministrador",
)


def _validar_base_local():
    if not settings.DEBUG:
        raise CommandError(
            "La inicialización solo está permitida con DEBUG activo."
        )

    configuracion = connection.settings_dict
    motor = str(configuracion.get("ENGINE", "")).lower()
    host = str(configuracion.get("HOST", "") or "").strip().lower()
    nombre = str(configuracion.get("NAME", "") or "").strip().lower()

    if "postgresql" not in motor:
        raise CommandError(
            "La inicialización requiere la base PostgreSQL local del proyecto."
        )
    if host not in {"localhost", "127.0.0.1", "::1"}:
        raise CommandError(
            "La inicialización solo puede ejecutarse sobre PostgreSQL local."
        )
    if nombre != "sipeip_db":
        raise CommandError(
            "La inicialización solo puede ejecutarse sobre la base sipeip_db."
        )


def _guardar_validado(instancia):
    instancia.full_clean()
    instancia.save()
    return instancia


def _actualizar_o_crear(modelo, lookup, defaults):
    instancia, _ = modelo.objects.get_or_create(**lookup, defaults=defaults)
    for campo, valor in defaults.items():
        setattr(instancia, campo, valor)
    return _guardar_validado(instancia)


class Command(BaseCommand):
    help = (
        "Inicializa roles, usuarios y registros institucionales de la base local."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            required=True,
            help="Contraseña temporal para los seis usuarios iniciales.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        _validar_base_local()
        password = str(options["password"] or "")
        if not password:
            raise CommandError("Debe proporcionar una contraseña temporal.")

        call_command("inicializar_rbac", stdout=self.stdout)
        self._inicializar_datos(password)
        self.stdout.write(
            self.style.SUCCESS(
                "Inicialización del sistema completada de forma idempotente."
            )
        )

    def _inicializar_datos(self, password):
        entidades, unidades = self._crear_estructura_institucional()
        usuarios = self._crear_usuarios(password, entidades, unidades)
        planes = self._crear_planificacion(entidades, usuarios)
        objetivos = self._crear_alineacion(entidades, usuarios)
        self._crear_proyecto(entidades, usuarios, planes, objetivos)
        self._crear_evento_inicial(entidades, usuarios)

    def _crear_estructura_institucional(self):
        secretaria = _actualizar_o_crear(
            EntidadInstitucional,
            {"codigo_oficial": "SNP"},
            {
                "nombre": "Secretaría Nacional de Planificación",
                "subsector": "Planificación nacional",
                "nivel_gobierno": "Nacional",
                "estado": EntidadInstitucional.Estado.ACTIVA,
            },
        )
        ministerio = _actualizar_o_crear(
            EntidadInstitucional,
            {"codigo_oficial": "MDI"},
            {
                "nombre": "Ministerio de Desarrollo Institucional",
                "subsector": "Administración pública",
                "nivel_gobierno": "Nacional",
                "estado": EntidadInstitucional.Estado.ACTIVA,
            },
        )

        especificaciones = (
            (
                "tecnologias",
                secretaria,
                "DTI",
                "Dirección de Tecnologías de la Información",
            ),
            (
                "planificacion_snp",
                secretaria,
                "DPLAN",
                "Dirección de Planificación",
            ),
            (
                "seguimiento",
                secretaria,
                "DSE",
                "Dirección de Seguimiento y Evaluación",
            ),
            (
                "planificacion_mdi",
                ministerio,
                "UPI",
                "Unidad de Planificación Institucional",
            ),
            (
                "administrativa_mdi",
                ministerio,
                "UADM",
                "Unidad Administrativa",
            ),
        )
        unidades = {}
        for clave, entidad, codigo, nombre in especificaciones:
            unidades[clave] = _actualizar_o_crear(
                UnidadOrganizacional,
                {"entidad": entidad, "codigo": codigo},
                {
                    "nombre": nombre,
                    "unidad_padre": None,
                    "estado": UnidadOrganizacional.Estado.ACTIVA,
                },
            )
        return {"secretaria": secretaria, "ministerio": ministerio}, unidades

    def _crear_usuarios(self, password, entidades, unidades):
        especificaciones = {
            "administrador": (
                "administrador_sistema",
                entidades["secretaria"],
                unidades["tecnologias"],
                "Administrador",
                "del Sistema",
                "administrador@snp.gob.ec",
            ),
            "planificador": (
                "planificador_institucional",
                entidades["ministerio"],
                unidades["planificacion_mdi"],
                "Planificador",
                "Institucional",
                "planificador@mdi.gob.ec",
            ),
            "supervisor": (
                "supervisor_planificacion",
                entidades["secretaria"],
                unidades["planificacion_snp"],
                "Supervisor",
                "de Planificación",
                "supervisor@snp.gob.ec",
            ),
            "externo": (
                "usuario_externo",
                entidades["ministerio"],
                unidades["administrativa_mdi"],
                "Usuario",
                "Externo",
                "externo@mdi.gob.ec",
            ),
            "auditor": (
                "auditor_control_interno",
                entidades["secretaria"],
                unidades["seguimiento"],
                "Auditor",
                "Institucional",
                "auditor@snp.gob.ec",
            ),
            "superadministrador": (
                "superadministrador_tecnico",
                entidades["secretaria"],
                unidades["tecnologias"],
                "Superadministrador",
                "Técnico",
                "superadministrador@snp.gob.ec",
            ),
        }

        usuarios = {}
        for username, datos in especificaciones.items():
            codigo_rol, entidad, unidad, nombres, apellidos, email = datos
            usuario, _ = Usuario.objects.get_or_create(username=username)
            usuario.rol = Rol.objects.get(codigo=codigo_rol)
            usuario.entidad = entidad
            usuario.unidad_organizacional = unidad
            usuario.first_name = nombres
            usuario.last_name = apellidos
            usuario.email = email
            usuario.estado = Usuario.EstadoUsuario.ACTIVO
            usuario.is_active = True
            usuario.is_staff = codigo_rol in {
                "administrador_sistema",
                "superadministrador_tecnico",
            }
            usuario.is_superuser = codigo_rol == "superadministrador_tecnico"
            usuario.set_password(password)
            usuarios[username] = _guardar_validado(usuario)
        return usuarios

    def _crear_planificacion(self, entidades, usuarios):
        plan_secretaria = _actualizar_o_crear(
            Plan,
            {
                "entidad": entidades["secretaria"],
                "nombre": "Plan Institucional 2026-2029",
            },
            {
                "descripcion": (
                    "Fortalece la planificación, el seguimiento y la evaluación "
                    "de las políticas públicas."
                ),
                "periodo_inicio": date(2026, 1, 1),
                "periodo_fin": date(2029, 12, 31),
                "responsable": usuarios["supervisor"],
                "creado_por": usuarios["administrador"],
                "estado": Plan.EstadoPlan.EN_REVISION,
                "activo": True,
            },
        )
        plan_ministerio = _actualizar_o_crear(
            Plan,
            {
                "entidad": entidades["ministerio"],
                "nombre": "Plan Institucional 2026-2029",
            },
            {
                "descripcion": (
                    "Orienta el fortalecimiento de la gestión y de los servicios "
                    "institucionales."
                ),
                "periodo_inicio": date(2026, 1, 1),
                "periodo_fin": date(2029, 12, 31),
                "responsable": usuarios["externo"],
                "creado_por": usuarios["planificador"],
                "estado": Plan.EstadoPlan.APROBADO,
                "activo": True,
            },
        )

        especificaciones = (
            (
                plan_secretaria,
                "Fortalecer el seguimiento de la planificación nacional",
                "Porcentaje de instrumentos de planificación con seguimiento",
                usuarios["administrador"],
                usuarios["supervisor"],
                Decimal("62.00"),
            ),
            (
                plan_ministerio,
                "Mejorar la capacidad de gestión institucional",
                "Porcentaje de procesos institucionales optimizados",
                usuarios["planificador"],
                None,
                Decimal("48.00"),
            ),
        )
        for plan, nombre_meta, nombre_indicador, registrador, validador, valor in especificaciones:
            meta = _actualizar_o_crear(
                Meta,
                {"plan": plan, "nombre": nombre_meta},
                {
                    "descripcion": "Resultado institucional previsto para el periodo.",
                    "resultado_esperado": (
                        "Incrementar el cumplimiento de los objetivos institucionales."
                    ),
                    "fecha_inicio": date(2026, 1, 1),
                    "fecha_fin": date(2026, 12, 31),
                    "estado": Meta.EstadoMeta.ACTIVA,
                    "activa": True,
                },
            )
            indicador = _actualizar_o_crear(
                Indicador,
                {"meta": meta, "nombre": nombre_indicador},
                {
                    "descripcion": "Mide el avance anual de la meta institucional.",
                    "unidad_medida": "Porcentaje",
                    "valor_base": Decimal("25.00"),
                    "valor_meta": Decimal("80.00"),
                    "valor_actual": valor,
                    "frecuencia": Indicador.FrecuenciaMedicion.TRIMESTRAL,
                    "activo": True,
                    "validado": validador is not None,
                    "validado_por": validador,
                    "fecha_validacion": (
                        timezone.make_aware(datetime(2026, 4, 2, 10, 0))
                        if validador
                        else None
                    ),
                },
            )
            _actualizar_o_crear(
                AvanceIndicador,
                {"indicador": indicador, "fecha_registro": date(2026, 6, 30)},
                {
                    "valor": valor,
                    "observacion": "Corte semestral del indicador institucional.",
                    "registrado_por": registrador,
                },
            )
        return {"secretaria": plan_secretaria, "ministerio": plan_ministerio}

    def _crear_alineacion(self, entidades, usuarios):
        eje = _actualizar_o_crear(
            EjePND,
            {"codigo": "EJE-REF-01"},
            {
                "nombre": "Institucionalidad y desarrollo sostenible",
                "descripcion": "Fortalecimiento de la gestión pública y sus resultados.",
                "estado": EstadoCatalogo.ACTIVO,
            },
        )
        objetivo_pnd = _actualizar_o_crear(
            ObjetivoPND,
            {"eje": eje, "codigo": "PND-REF-01"},
            {
                "nombre": "Fortalecer las capacidades institucionales del Estado",
                "descripcion": "Mejora la eficiencia y calidad de la gestión pública.",
                "estado": EstadoCatalogo.ACTIVO,
            },
        )
        ods = _actualizar_o_crear(
            ODS,
            {"numero": 16},
            {
                "nombre": "Paz, justicia e instituciones sólidas",
                "descripcion": "Promueve instituciones eficaces y responsables.",
                "estado": EstadoCatalogo.ACTIVO,
            },
        )

        objetivos = {}
        especificaciones = (
            (
                "secretaria",
                entidades["secretaria"],
                "OEI-01",
                "Fortalecer el Sistema Nacional de Planificación",
                usuarios["administrador"],
                usuarios["supervisor"],
            ),
            (
                "ministerio",
                entidades["ministerio"],
                "OEI-01",
                "Incrementar la eficiencia de la gestión institucional",
                usuarios["planificador"],
                usuarios["superadministrador"],
            ),
        )
        for clave, entidad, codigo, nombre, creador, validador in especificaciones:
            objetivo = _actualizar_o_crear(
                ObjetivoEstrategico,
                {"entidad": entidad, "codigo": codigo},
                {
                    "nombre": nombre,
                    "descripcion": "Objetivo estratégico del periodo institucional.",
                    "estado": EstadoCatalogo.ACTIVO,
                },
            )
            _actualizar_o_crear(
                Alineacion,
                {
                    "objetivo_estrategico": objetivo,
                    "objetivo_pnd": objetivo_pnd,
                    "ods": ods,
                },
                {
                    "justificacion": (
                        "La gestión institucional contribuye al fortalecimiento "
                        "de instituciones eficaces y responsables."
                    ),
                    "estado": Alineacion.EstadoAlineacion.VALIDADA,
                    "usuario_creador": creador,
                    "usuario_validador": validador,
                },
            )
            objetivos[clave] = objetivo
        return objetivos

    def _crear_proyecto(self, entidades, usuarios, planes, objetivos):
        tipologia = _actualizar_o_crear(
            TipologiaIntervencion,
            {"codigo": "FORT-INST"},
            {
                "nombre": "Fortalecimiento institucional",
                "descripcion": "Intervenciones para mejorar capacidades y servicios.",
                "activo": True,
            },
        )
        proyecto = _actualizar_o_crear(
            ProyectoInversion,
            {"entidad": entidades["ministerio"], "codigo": "PIR-001"},
            {
                "plan": planes["ministerio"],
                "objetivo_estrategico": objetivos["ministerio"],
                "nombre": "Modernización de la gestión institucional",
                "descripcion": (
                    "Mejora procesos, capacidades y servicios de la institución."
                ),
                "tipologia_intervencion": tipologia,
                "responsable": usuarios["externo"],
                "creado_por": usuarios["planificador"],
                "fecha_inicio": date(2026, 1, 1),
                "fecha_fin": date(2026, 12, 31),
                "presupuesto_estimado": Decimal("180000.00"),
                "avance_fisico": Decimal("35.00"),
                "avance_financiero": Decimal("30.00"),
                "estado": ProyectoInversion.EstadoProyecto.EN_EJECUCION,
                "activo": True,
            },
        )
        hito = _actualizar_o_crear(
            HitoProyecto,
            {"proyecto": proyecto, "orden": 1},
            {
                "nombre": "Optimización de procesos prioritarios",
                "descripcion": "Revisión e implementación de procesos institucionales.",
                "fecha_inicio_planificada": date(2026, 1, 1),
                "fecha_fin_planificada": date(2026, 9, 30),
                "porcentaje_planificado": Decimal("100.00"),
                "activo": True,
            },
        )
        _actualizar_o_crear(
            SeguimientoProyecto,
            {"proyecto": proyecto, "fecha_registro": date(2026, 6, 30)},
            {
                "hito": hito,
                "avance_fisico": Decimal("35.00"),
                "avance_financiero": Decimal("30.00"),
                "observacion": "Corte semestral de ejecución del proyecto.",
                "registrado_por": usuarios["planificador"],
            },
        )

    def _crear_evento_inicial(self, entidades, usuarios):
        _actualizar_o_crear(
            EventoAuditoria,
            {
                "modulo": "sistema",
                "funcionalidad": "Inicialización del sistema",
                "accion": "INICIALIZAR",
                "tipo_entidad": "sistema",
                "registro_id": "catalogos-iniciales",
            },
            {
                "usuario": usuarios["superadministrador"],
                "usuario_identificador": usuarios["superadministrador"].username,
                "entidad": entidades["secretaria"],
                "valores_anteriores": {},
                "valores_posteriores": {
                    "usuarios": list(USUARIOS_INICIALES),
                    "entidades": ["SNP", "MDI"],
                },
                "resultado": EventoAuditoria.Resultado.EXITO,
                "detalle": "Catálogos y registros institucionales inicializados.",
            },
        )
