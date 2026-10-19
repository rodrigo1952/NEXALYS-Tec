from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tiendas", "0003_refrigerio"),
    ]

    operations = [
        migrations.AddField(
            model_name="tienda",
            name="motivo_suspension",
            field=models.TextField(
                blank=True,
                help_text="La tienda lo ve en su panel para saber qué corregir.",
                verbose_name="motivo de la suspensión",
            ),
        ),
    ]
