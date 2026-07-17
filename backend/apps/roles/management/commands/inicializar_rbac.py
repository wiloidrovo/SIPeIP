"""Inicializa de forma idempotente los roles institucionales aprobados."""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.roles.models import Rol
from apps.roles.permissions import BASE_ROLES


class Command(BaseCommand):
    help = "Crea o actualiza el catálogo de roles base de SIPeIP."

    @transaction.atomic
    def handle(self, *args, **options):
        creados = 0
        actualizados = 0

        for codigo, definicion in BASE_ROLES.items():
            rol = Rol.objects.filter(codigo=codigo).first()
            politica_inicial = rol is None

            if rol is None:
                rol = Rol.objects.filter(
                    nombre__iexact=definicion["nombre"]
                ).first()
                politica_inicial = rol is None or rol.codigo != codigo

            if rol is None and codigo == "administrador_sistema":
                rol = Rol.objects.filter(nombre__iexact="Administrador").first()

            if rol is None:
                rol = Rol(codigo=codigo)
                creados += 1
            else:
                actualizados += 1

            conflicto_nombre = (
                Rol.objects.filter(nombre__iexact=definicion["nombre"])
                .exclude(pk=rol.pk)
                .exists()
            )
            if conflicto_nombre:
                raise CommandError(
                    f"Existe otro rol con el nombre '{definicion['nombre']}'."
                )

            rol.codigo = codigo
            rol.nombre = definicion["nombre"]
            rol.descripcion = definicion["descripcion"]
            rol.permisos = list(definicion["permisos"])
            if politica_inicial:
                rol.alcance = definicion["alcance"]
            rol.full_clean()
            rol.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"RBAC inicializado: {creados} rol(es) creados y "
                f"{actualizados} rol(es) actualizados."
            )
        )
