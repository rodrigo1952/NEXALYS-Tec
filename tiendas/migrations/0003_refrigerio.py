from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tiendas", "0002_logo_horario"),
    ]

    operations = [
        migrations.AddField(
            model_name="horariodia",
            name="descanso_inicio",
            field=models.TimeField(blank=True, null=True, verbose_name="inicio del refrigerio"),
        ),
        migrations.AddField(
            model_name="horariodia",
            name="descanso_fin",
            field=models.TimeField(blank=True, null=True, verbose_name="fin del refrigerio"),
        ),
    ]
