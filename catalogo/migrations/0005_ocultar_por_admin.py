from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalogo", "0004_ofertas_destacados_fotos_busqueda"),
    ]

    operations = [
        migrations.AddField(
            model_name="producto",
            name="oculto_por_admin",
            field=models.BooleanField(
                default=False,
                help_text="El administrador lo ocultó del catálogo; la tienda no puede volver a publicarlo.",
                verbose_name="oculto por el administrador",
            ),
        ),
        migrations.AddField(
            model_name="producto",
            name="motivo_ocultamiento",
            field=models.TextField(blank=True, verbose_name="motivo del ocultamiento"),
        ),
    ]
