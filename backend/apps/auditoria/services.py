from datetime import date, datetime
from decimal import Decimal

from django.db import models, transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response

from .models import EventoAuditoria


CLAVES_SENSIBLES = (
    "password",
    "contraseña",
    "secret",
    "secreto",
    "token",
    "cookie",
)


def _es_clave_sensible(clave):
    normalizada = str(clave).lower()
    return any(fragmento in normalizada for fragmento in CLAVES_SENSIBLES)


def sanitizar_valor(valor):
    if isinstance(valor, dict):
        return {
            str(clave): sanitizar_valor(contenido)
            for clave, contenido in valor.items()
            if not _es_clave_sensible(clave)
        }
    if isinstance(valor, (list, tuple, set)):
        return [sanitizar_valor(item) for item in valor]
    if isinstance(valor, (datetime, date)):
        return valor.isoformat()
    if isinstance(valor, Decimal):
        return str(valor)
    if isinstance(valor, models.Model):
        return valor.pk
    if valor is None or isinstance(valor, (str, int, float, bool)):
        return valor
    return str(valor)


def serializar_instancia(instancia):
    if instancia is None:
        return {}

    datos = {}
    for campo in instancia._meta.concrete_fields:
        if _es_clave_sensible(campo.name):
            continue
        valor = getattr(instancia, campo.attname)
        datos[campo.name] = sanitizar_valor(valor)
    return datos


def obtener_direccion_ip(request):
    if request is None:
        return None
    return request.META.get("REMOTE_ADDR") or None


def obtener_entidad(instancia=None, usuario=None, entidad=None):
    if entidad is not None:
        return entidad
    if instancia is not None:
        if getattr(instancia._meta, "label_lower", "") == (
            "configuracion.entidadinstitucional"
        ):
            return instancia
        directa = getattr(instancia, "entidad", None)
        if directa is not None:
            return directa
        plan = getattr(instancia, "plan", None)
        if plan is not None:
            return getattr(plan, "entidad", None)
        meta = getattr(instancia, "meta", None)
        if meta is not None and getattr(meta, "plan", None) is not None:
            return getattr(meta.plan, "entidad", None)
        indicador = getattr(instancia, "indicador", None)
        if indicador is not None:
            return getattr(indicador.meta.plan, "entidad", None)
    return getattr(usuario, "entidad", None) if usuario is not None else None


def registrar_evento(
    *,
    request=None,
    modulo,
    funcionalidad,
    accion,
    instancia=None,
    antes=None,
    despues=None,
    resultado=EventoAuditoria.Resultado.EXITO,
    detalle="",
    usuario=None,
    entidad=None,
    identificador="",
):
    actor = usuario
    if actor is None and request is not None:
        candidato = getattr(request, "user", None)
        if getattr(candidato, "is_authenticated", False):
            actor = candidato

    tipo_entidad = ""
    registro_id = ""
    if instancia is not None:
        tipo_entidad = instancia._meta.label
        registro_id = str(instancia.pk or "")

    evento = EventoAuditoria.objects.create(
        usuario=actor,
        usuario_identificador=(
            getattr(actor, "username", "") if actor else str(identificador)[:150]
        ),
        entidad=obtener_entidad(instancia, actor, entidad),
        modulo=modulo,
        funcionalidad=funcionalidad,
        accion=accion,
        tipo_entidad=tipo_entidad,
        registro_id=registro_id,
        valores_anteriores=sanitizar_valor(antes or {}),
        valores_posteriores=sanitizar_valor(
            despues if despues is not None else serializar_instancia(instancia)
        ),
        direccion_ip=obtener_direccion_ip(request),
        resultado=resultado,
        detalle=str(detalle)[:2000],
    )
    if request is not None:
        request_http = getattr(request, "_request", request)
        setattr(request_http, "_sipeip_auditoria_registrada", True)
    return evento


class AuditoriaModelViewSetMixin:
    audit_modulo = "sistema"
    audit_funcionalidad = "gestión"

    def _obtener_instancia_bloqueada(self, instancia_autorizada):
        modelo = type(instancia_autorizada)
        modelo._default_manager.select_for_update().get(
            pk=instancia_autorizada.pk
        )
        queryset = self.filter_queryset(self.get_queryset())
        instancia = get_object_or_404(queryset, pk=instancia_autorizada.pk)
        self.check_object_permissions(self.request, instancia)
        return instancia

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        autorizada = self.get_object()
        instancia = self._obtener_instancia_bloqueada(autorizada)
        serializer = self.get_serializer(
            instancia,
            data=request.data,
            partial=partial,
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instancia, "_prefetched_objects_cache", None):
            instancia._prefetched_objects_cache = {}

        return Response(serializer.data, status=status.HTTP_200_OK)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        autorizada = self.get_object()
        instancia = self._obtener_instancia_bloqueada(autorizada)
        self.perform_destroy(instancia)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @transaction.atomic
    def perform_create(self, serializer):
        instancia = serializer.save()
        registrar_evento(
            request=self.request,
            modulo=self.audit_modulo,
            funcionalidad=self.audit_funcionalidad,
            accion="CREAR",
            instancia=instancia,
        )

    @transaction.atomic
    def perform_update(self, serializer):
        antes = serializar_instancia(serializer.instance)
        instancia = serializer.save()
        registrar_evento(
            request=self.request,
            modulo=self.audit_modulo,
            funcionalidad=self.audit_funcionalidad,
            accion="EDITAR",
            instancia=instancia,
            antes=antes,
        )

    @transaction.atomic
    def perform_destroy(self, instance):
        antes = serializar_instancia(instance)
        tipo_entidad = instance._meta.label
        registro_id = str(instance.pk)
        entidad = obtener_entidad(instance, getattr(self.request, "user", None))
        instance.delete()
        EventoAuditoria.objects.create(
            usuario=self.request.user,
            usuario_identificador=self.request.user.username,
            entidad=entidad,
            modulo=self.audit_modulo,
            funcionalidad=self.audit_funcionalidad,
            accion="ELIMINAR",
            tipo_entidad=tipo_entidad,
            registro_id=registro_id,
            valores_anteriores=antes,
            valores_posteriores={},
            direccion_ip=obtener_direccion_ip(self.request),
            resultado=EventoAuditoria.Resultado.EXITO,
        )
