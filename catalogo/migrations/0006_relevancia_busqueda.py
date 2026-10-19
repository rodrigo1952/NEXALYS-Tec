"""
Búsqueda por relevancia: además del texto completo, cada producto guarda su
nombre y su marca + categoría sin tildes, para que "Más relevantes" ponga primero
lo que coincide en el nombre. Al final llena esos campos en los productos que ya existían.
"""

from django.db import migrations, models

from catalogo.busqueda import normalizar


def llenar_campos(apps, schema_editor):
    Producto = apps.get_model("catalogo", "Producto")
    for producto in Producto.objects.select_related("marca", "categoria"):
        Producto.objects.filter(pk=producto.pk).update(
            nombre_busqueda=normalizar(producto.nombre),
            etiquetas_busqueda=normalizar(f"{producto.marca.nombre} {producto.categoria.nombre}"),
        )


class Migration(migrations.Migration):

    dependencies = [
        ("catalogo", "0005_ocultar_por_admin"),
    ]

    operations = [
        migrations.AddField(
            model_name="producto",
            name="nombre_busqueda",
            field=models.TextField(blank=True, editable=False, verbose_name="nombre para buscar"),
        ),
        migrations.AddField(
            model_name="producto",
            name="etiquetas_busqueda",
            field=models.TextField(blank=True, editable=False, verbose_name="marca y categoría para buscar"),
        ),
        migrations.RunPython(llenar_campos, migrations.RunPython.noop),
    ]
