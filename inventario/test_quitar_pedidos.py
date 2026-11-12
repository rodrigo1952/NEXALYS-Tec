"""La app «pedidos» se quitó: su migración de limpieza borra los restos que dejó en la base de datos."""

from importlib import import_module
from types import SimpleNamespace

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder
from django.test import TestCase

limpieza = import_module("inventario.migrations.0005_quitar_app_pedidos")


class QuitarPedidosTests(TestCase):
    def test_la_app_ya_no_esta_ni_su_tabla(self):
        self.assertFalse(apps.is_installed("pedidos"))
        self.assertNotIn("pedidos_pedido", connection.introspection.table_names())

    def test_borra_sus_restos_y_nada_mas(self):
        ContentType.objects.create(app_label="pedidos", model="pedido")
        recorder = MigrationRecorder(connection)
        recorder.record_applied("pedidos", "0003_retirar_pedidos")
        otras = recorder.migration_qs.exclude(app="pedidos").count()

        limpieza.limpiar(apps, SimpleNamespace(connection=connection))  # solo usa la conexión

        self.assertFalse(ContentType.objects.filter(app_label="pedidos").exists())
        self.assertFalse(recorder.migration_qs.filter(app="pedidos").exists())
        self.assertEqual(recorder.migration_qs.count(), otras)
