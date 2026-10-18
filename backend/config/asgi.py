"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Punto de entrada para un servidor compatible con ASGI; no inicia un servidor
# por sí solo ni añade integraciones o canales de comunicación adicionales.
application = get_asgi_application()
