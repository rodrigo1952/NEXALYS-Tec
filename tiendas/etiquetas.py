"""
Etiquetas que diferencian a cada tienda (nov 2026): se ven en el Inicio, en su perfil y en Tiendas cercanas.

  lema           la frase corta que escribió la tienda («Especialistas en laptops»)     → dorada
  servicios      los que marcó en «Editar datos» y su «otro servicio»                    → cian, con ícono
  especialidades salen SOLAS de lo que vende: una categoría es su especialidad si tiene  → grises
                 al menos 2 productos publicados y es el 30 % o más de su catálogo
                 (máximo 2, sin «Otros»). Así la tienda no tiene que llenar nada y no
                 puede decir que vende algo que no vende.
"""

from collections import defaultdict

from django.db.models import Count

MINIMO_PRODUCTOS = 2
PROPORCION_MINIMA = 0.3
MAXIMO_ESPECIALIDADES = 2


def especialidades_por_tienda(ids_tiendas):
    """{id de tienda: [{"id": id de la categoría, "texto": nombre}, ...]} para varias tiendas en una sola consulta."""
    from catalogo.models import Producto  # aquí para no crear un import circular

    filas = (
        Producto.objects.visibles()
        .filter(tienda_id__in=list(ids_tiendas))
        .values("tienda_id", "categoria_id", "categoria__nombre")
        .annotate(cantidad=Count("id"))
    )
    por_tienda = defaultdict(list)
    for fila in filas:
        por_tienda[fila["tienda_id"]].append(fila)

    resultado = {}
    for tienda_id, categorias in por_tienda.items():
        total = sum(c["cantidad"] for c in categorias)
        elegidas = [
            c for c in categorias
            if c["cantidad"] >= MINIMO_PRODUCTOS
            and c["cantidad"] / total >= PROPORCION_MINIMA
            and c["categoria__nombre"].strip().lower() != "otros"
        ]
        elegidas.sort(key=lambda c: (-c["cantidad"], c["categoria__nombre"].lower()))
        resultado[tienda_id] = [
            {"id": c["categoria_id"], "texto": c["categoria__nombre"]} for c in elegidas[:MAXIMO_ESPECIALIDADES]
        ]
    return resultado


def etiquetas(tienda, especialidades, maximo=None):
    """Lista para dibujar: [{"texto", "tipo": lema|servicio|especialidad, "icono"}], en ese orden."""
    lista = []
    if tienda.lema:
        lista.append({"texto": tienda.lema, "tipo": "lema", "icono": "stars"})
    for servicio in tienda.servicios():
        lista.append({"texto": servicio["texto"], "tipo": "servicio", "icono": servicio["icono"]})
    for especialidad in especialidades:
        lista.append({"texto": especialidad["texto"], "tipo": "especialidad", "icono": ""})
    return lista[:maximo] if maximo else lista
