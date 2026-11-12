"""
Etapa 5: aquí los pedidos del antiguo módulo Pedidos se convirtieron en ventas
(con origen «Pedido #N», el celular del cliente en la nota y método de pago «Otro»).

Esa conversión ya se hizo en todas las bases de datos que tenían pedidos. Después se
quitó la app «pedidos» del proyecto, así que esta migración quedó vacía: se conserva
solo para que el orden de las migraciones siga igual en las PC donde ya se ejecutó.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("inventario", "0003_ingresos_ajustes"),
    ]

    operations = []
