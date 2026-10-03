def roles(request):
    """Indica a todas las plantillas qué rol tiene el usuario, para armar el menú."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {"es_admin": False, "es_tienda": False, "es_cliente": False, "tienda_actual": None}

    nombres = set(user.groups.values_list("name", flat=True))
    tienda = getattr(user, "tienda", None)
    return {
        "es_admin": user.is_superuser or "Administrador" in nombres,
        "es_tienda": tienda is not None,
        "es_cliente": "Cliente" in nombres,
        "tienda_actual": tienda,
    }
