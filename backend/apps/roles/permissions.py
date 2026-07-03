"""
Catálogo centralizado de permisos del sistema.
Cualquier permiso asignado a un rol debe existir en esta lista.
"""
ALLOWED_ROLE_PERMISSIONS = [
    "usuarios.ver",
    "usuarios.crear",
    "usuarios.editar",
    "usuarios.eliminar",
    "roles.ver",
    "roles.crear",
    "roles.editar",
    "roles.eliminar",
    "roles.asignar_permisos",
]