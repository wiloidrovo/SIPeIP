"""Configuración aislada para la suite automatizada local.

Evita requerir permisos para crear una base PostgreSQL adicional y nunca toca
la base de desarrollo configurada en ``.env``.
"""

from .settings import *  # noqa: F403


DATABASES = {  # noqa: F405
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Las claves creadas por las pruebas son aleatorias y efímeras. Este hasher
# reduce el tiempo de ejecución sin alterar la configuración de la aplicación.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
