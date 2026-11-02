from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock
from django.contrib.auth.hashers import check_password
from django.test import SimpleTestCase
from bson import ObjectId, json_util
from .data_pipeline import clean_document, reset_passwords, export_mongo


class PipelineTests(SimpleTestCase):
    def test_cleaning_keeps_bson_ids_and_hashes(self):
        identity = ObjectId()
        result = clean_document({'_id': identity, 'usuario_id': ' usr ', 'password_hash': 'hash ', 'nombre': ' Ana ', 'password': 'secreto'})
        self.assertEqual(result['_id'], identity)
        self.assertEqual(result['password_hash'], 'hash ')
        self.assertEqual(result['usuario_id'], ' usr ')
        self.assertEqual(result['nombre'], 'Ana')
        self.assertNotIn('password', result)

    def test_reset_uses_distinct_salts_and_consistent_company_links(self):
        db = MagicMock(); db.list_collection_names.return_value = ['usuarios_empresas_roles']
        docs = [{'_id': '1', 'usuario_id': 'u1', 'password_hash': 'old'},
                {'_id': '2', 'usuario_id': 'u1'}, {'_id': '3', 'usuario_id': 'u2', 'password_hash': 'other'}]
        col = db.__getitem__.return_value
        def find(*args):
            return iter([dict(doc) for doc in docs])
        def update(query, changes):
            for doc in docs:
                if doc['_id'] == query['_id']:
                    doc.update(changes['$set'])
                    return MagicMock(matched_count=1, modified_count=1)
        col.find.side_effect = find; col.update_one.side_effect = update
        report = {}; reset_passwords(db, 'test-only-password', report)
        self.assertEqual(report['verificados'], 3)
        self.assertEqual(docs[0]['password_hash'], docs[1]['password_hash'])
        self.assertNotEqual(docs[0]['password_hash'], docs[2]['password_hash'])
        self.assertTrue(all(check_password('test-only-password', doc['password_hash']) for doc in docs))

    def test_export_mongo_preserves_bson_and_excludes_plain_password(self):
        db = MagicMock(); db.list_collection_names.return_value = ['usuarios_empresas_roles']
        identity = ObjectId()
        db.__getitem__.return_value.find.return_value.batch_size.return_value = [{'_id': identity, 'password_hash': 'hash', 'password': 'plain'}]
        with TemporaryDirectory() as folder:
            target = Path(folder) / 'mongo.jsonl'
            self.assertEqual(export_mongo(db, target), {'usuarios_empresas_roles': 1})
            row = json_util.loads(target.read_text(encoding='utf-8'))
            self.assertEqual(row['documento']['_id'], identity)
            self.assertEqual(row['documento']['password_hash'], 'hash')
            self.assertNotIn('password', row['documento'])

    def test_command_writes_sources_to_separate_directories(self):
        from unittest.mock import patch
        from django.core.management import call_command
        with TemporaryDirectory() as folder:
            def export_sql(name, **kwargs):
                Path(kwargs['salida']).write_text('sql-only', encoding='utf-8')
                kwargs['stdout'].write('{"registros": {"dbo.Pedido": 1}}')
            with patch('Tradconnect_no_sql.management.commands.extraer_bases.get_database') as get_db, patch('Tradconnect_no_sql.management.commands.extraer_bases.call_command', side_effect=export_sql), patch('Tradconnect_no_sql.management.commands.extraer_bases.export_mongo', return_value={'usuarios_empresas_roles': 2}) as export:
                call_command('extraer_bases', fuente='ambas', directorio=folder, stdout=StringIO())
            self.assertTrue((Path(folder) / 'sql' / 'datos_limpios.jsonl').exists())
            self.assertEqual(export.call_args.args[1], Path(folder) / 'nosql' / 'datos_limpios.jsonl')

    def test_reset_rejects_sql_only_source(self):
        from django.core.management import call_command, CommandError
        with TemporaryDirectory() as folder:
            with self.assertRaisesMessage(CommandError, 'requiere --fuente mongo'):
                call_command('extraer_bases', fuente='sql', directorio=folder, restablecer_passwords=True, stdout=StringIO())
