from django.test import SimpleTestCase
from django.contrib.auth.hashers import check_password, make_password
from .cleaning import clean_value, prepare_password


class CleaningTests(SimpleTestCase):
    def test_cleaning_keeps_inner_spaces(self):
        self.assertEqual(clean_value('  Cafe\u0301  local\x00  '), 'Caf\u00e9  local')
        self.assertEqual(clean_value(123), 123)

    def test_plaintext_preserves_password_spaces(self):
        hashed, state = prepare_password('  clave real  ')
        self.assertEqual(state, 'hasheado')
        self.assertTrue(check_password('  clave real  ', hashed))

    def test_valid_hash_is_not_hashed_twice(self):
        hashed = make_password('secreto')
        self.assertEqual(prepare_password(hashed), (hashed, 'conservado'))

    def test_empty_password_cannot_authenticate(self):
        hashed, state = prepare_password('')
        self.assertEqual(state, 'sin_clave')
        self.assertFalse(check_password('', hashed))

    def test_unknown_hash_requires_review(self):
        self.assertEqual(prepare_password('unknown$hash')[1], 'revisar')
        self.assertEqual(prepare_password('pbkdf2_sha256$broken')[1], 'revisar')


class ExtractionCommandTests(SimpleTestCase):
    def test_reads_real_columns_instead_of_orm(self):
        import json
        from io import StringIO
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from unittest.mock import patch, MagicMock
        from django.core.management import call_command
        cursor = MagicMock()
        cursor.fetchall.side_effect = [[('dbo', 'DetallePedido')], [('Id',)]]
        cursor.description = [('Id',), ('MontoDescuento',)]
        cursor.fetchmany.side_effect = [[(1, '  real  ')], []]
        with TemporaryDirectory() as folder:
            target = Path(folder) / 'export.jsonl'
            with patch('Tradconnect_no_sql.management.commands.extraer_datos.connection') as db:
                db.cursor.return_value.__enter__.return_value = cursor
                db.ops.quote_name.side_effect = lambda name: '[' + name + ']'
                call_command('extraer_datos', salida=str(target), stdout=StringIO(), stderr=StringIO())
            record = json.loads(target.read_text(encoding='utf-8'))
            self.assertEqual(record['documento'], {'Id': 1, 'MontoDescuento': 'real'})
            self.assertTrue(any(call.args[0] == 'SELECT * FROM [dbo].[DetallePedido]' for call in cursor.execute.call_args_list))

    def test_existing_output_is_preserved(self):
        from io import StringIO
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from django.core.management import call_command, CommandError
        with TemporaryDirectory() as folder:
            target = Path(folder) / 'existing.jsonl'
            target.write_text('original', encoding='utf-8')
            with self.assertRaisesMessage(CommandError, 'El archivo ya existe'):
                call_command('extraer_datos', salida=str(target), stdout=StringIO())
            self.assertEqual(target.read_text(encoding='utf-8'), 'original')

    def test_database_error_identifies_table_without_leaking_values(self):
        from io import StringIO
        from unittest.mock import patch, MagicMock
        from django.core.management import call_command, CommandError
        from django.db import ProgrammingError
        cursor = MagicMock()
        cursor.fetchall.side_effect = [[('dbo', 'DetallePedido')], [('Id',)]]
        cursor.execute.side_effect = [None, None, ProgrammingError('42S22 secret-value')]
        with patch('Tradconnect_no_sql.management.commands.extraer_datos.connection') as db:
            db.cursor.return_value.__enter__.return_value = cursor
            db.ops.quote_name.side_effect = lambda name: '[' + name + ']'
            with self.assertRaises(CommandError) as error:
                call_command('extraer_datos', stdout=StringIO())
        self.assertIn('dbo.DetallePedido', str(error.exception))
        self.assertIn('42S22', str(error.exception))
        self.assertNotIn('secret-value', str(error.exception))
