"""
Etapa 5: se retira el módulo Pedidos. Sus datos ya se convirtieron en ventas
(inventario/migrations/0004_convertir_pedidos.py), así que la tabla se elimina.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("pedidos", "0002_conservar_ventas_anonimas"),
        ("inventario", "0004_convertir_pedidos"),
    ]

    operations = [
        migrations.DeleteModel(name="Pedido"),
    ]
