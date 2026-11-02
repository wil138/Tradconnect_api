import json
from pathlib import Path
from tempfile import TemporaryDirectory
from django.test import SimpleTestCase
from django.core.management.base import CommandError
from bson import ObjectId
from .restore_data import load_sources, sort_tables, fingerprint, sql_value


class RestoreTests(SimpleTestCase):
    def test_parent_tables_inserted_first(self):
        parent = ('dbo', 'Pedido'); child = ('dbo', 'DetallePedido')
        self.assertEqual(sort_tables([child, parent], [(child, parent)]), [parent, child])

    def test_cycle_rejected_without_disabling_constraints(self):
        with self.assertRaises(CommandError):
            sort_tables(['a', 'b'], [('a', 'b'), ('b', 'a')])

    def test_fingerprint_preserves_bson_and_ignores_row_order(self):
        a = {'_id': ObjectId(), 'nombre': ' A '}; b = {'_id': ObjectId()}
        self.assertEqual(fingerprint([a, b]), fingerprint([b, a]))
        self.assertNotEqual(fingerprint([a]), fingerprint([{**a, 'nombre': 'A'}]))

    def test_duplicate_mongo_ids_rejected(self):
        with TemporaryDirectory() as folder:
            root = Path(folder); (root/'sql').mkdir(); (root/'nosql').mkdir()
            (root/'sql'/'datos_limpios.jsonl').write_text(json.dumps({'coleccion':'pedido', 'documento':{'Id':1}})+'\n')
            row = json.dumps({'coleccion':'usuarios_empresas_roles', 'documento':{'_id':'u1'}})+'\n'
            (root/'nosql'/'datos_limpios.jsonl').write_text(row+row)
            with self.assertRaisesMessage(CommandError, 'duplicados'):
                load_sources(root)

    def test_sql_datetimes_are_typed_and_converted_to_utc(self):
        from datetime import datetime
        self.assertEqual(sql_value('2026-10-23T08:00:00-06:00', 'datetime'), datetime(2026,10,23,14,0))
        self.assertIsNone(sql_value(None, 'datetime'))
