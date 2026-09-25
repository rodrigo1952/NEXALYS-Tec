def roles(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {"es_admin": False, "es_vendedor": False, "es_cliente": False}

    nombres = set(user.groups.values_list("name", flat=True))
    es_admin = user.is_superuser or "Administrador" in nombres
    return {
        "es_admin": es_admin,
        "es_vendedor": es_admin or "Vendedor" in nombres,
        "es_cliente": "Cliente" in nombres,
    }