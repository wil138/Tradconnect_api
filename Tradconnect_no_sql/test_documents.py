import json
from datetime import datetime, timezone
from tempfile import TemporaryDirectory
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase
from pydantic import ValidationError
from rest_framework.test import APIRequestFactory, force_authenticate

from .document_views import CollectionView
from .models import (SCHEMAS, UsuarioEmpresaRolCreate, UsuarioEmpresaRolRead,
                     PreferenciaNegocioRead, TransaccionNoExitosaCreate)


class DocumentTests(SimpleTestCase):
    def test_example_matches_schemas(self):
        fixture = Path(__file__).parent / 'fixtures' / 'ejemplo.json'
        for name, documents in json.loads(fixture.read_text(encoding='utf-8')).items():
            for document in documents:
                with self.subTest(collection=name):
                    SCHEMAS[name][1].model_validate(document)

    def user_data(self):
        return dict(empresa_id='emp_1', razon_social='Restaurante', ruc='RUC1',
                    tipo_empresa='Restaurante', usuario_id='usr_1', nombre_usuario='Ana',
                    correo='ana@example.com', password_hash='secreto', estado_usuario=True,
                    rol_id=1, nombre_rol='Cliente', estado_rol=True,
                    fecha_asignacion=datetime.now(timezone.utc), fecha_registro=datetime.now(timezone.utc))

    def test_company_role_validation(self):
        payload = self.user_data()
        payload['tipo_empresa'] = 'Proveedor'
        with self.assertRaises(ValidationError):
            UsuarioEmpresaRolCreate.model_validate(payload)

    def test_hash_never_in_read_response(self):
        result = UsuarioEmpresaRolRead.model_validate({'_id': 'uer_1', **self.user_data()})
        self.assertNotIn('password_hash', result.model_dump(mode='json', by_alias=True))

    def test_read_alias_and_extra_fields(self):
        result = PreferenciaNegocioRead.model_validate(dict(
            _id='pref_1', empresa_id='emp_1', usuario_id='usr_1',
            horario_entrega_preferido='08:00', fecha_actualizacion='2026-01-01T08:00:00Z', extra='ignore'))
        self.assertEqual(result.id, 'pref_1')
        self.assertNotIn('extra', result.model_dump())

    def test_all_collections_and_invalid_numeric_values(self):
        self.assertEqual(len(SCHEMAS), 13)
        payload = dict(fecha_intento='2026-01-01T08:00:00Z', cliente_empresa_id='1',
                       cliente_nombre='A', proveedor_empresa_id='2', proveedor_nombre='B', motivo='Sin stock')
        for amount in ('-1', 'NaN', 'Infinity'):
            with self.subTest(amount=amount), self.assertRaises(ValidationError):
                TransaccionNoExitosaCreate.model_validate({**payload, 'monto_tentativo': amount})

    @patch('Tradconnect_no_sql.document_views.get_database')
    def test_list_hides_hash(self, database):
        cursor = database.return_value.__getitem__.return_value.find.return_value
        cursor.sort.return_value.skip.return_value.limit.return_value = [{'_id': 'uer_1', **self.user_data()}]
        request = APIRequestFactory().get('/api/nosql/usuarios_empresas_roles/')
        force_authenticate(request, SimpleNamespace(is_authenticated=True,
                           rolid=SimpleNamespace(nombrerol='Administrador')))
        response = CollectionView.as_view()(request, collection='usuarios_empresas_roles')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('password_hash', response.data['results'][0])

    @patch('Tradconnect_no_sql.management.commands.cargar_documentos_nosql.get_database')
    def test_import_validates_entire_file_before_writing(self, database):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'data.json'
            path.write_text(json.dumps({'preferencias_negocio': [dict(
                _id='pref_1', empresa_id='1', usuario_id='1', horario_entrega_preferido='08:00',
                fecha_actualizacion='2026-01-01T08:00:00Z'), {'_id': 'invalid'}]}), encoding='utf-8')
            with self.assertRaises(CommandError):
                call_command('cargar_documentos_nosql', str(path))
        database.return_value.__getitem__.return_value.bulk_write.assert_not_called()

    @patch('Tradconnect_no_sql.services.sql.Categoria.objects.filter')
    def test_missing_sql_reference_is_rejected(self, category):
        from rest_framework.exceptions import ValidationError as APIValidationError
        from .services import validate_document
        category.return_value.exists.return_value = False
        with self.assertRaises(APIValidationError):
            validate_document('preferencias_categorias', {'preferencia_id': 'pref_1', 'categoria_id_sql': 77}, MagicMock())

    @patch('Tradconnect_no_sql.management.commands.cargar_documentos_nosql.get_database')
    def test_import_upserts_stable_ids_and_dry_run_does_not_write(self, database):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'data.json'
            path.write_text(json.dumps({'preferencias_negocio': [dict(
                _id='pref_1', empresa_id='1', usuario_id='1', horario_entrega_preferido='08:00',
                fecha_actualizacion='2026-01-01T08:00:00Z')]}), encoding='utf-8')
            call_command('cargar_documentos_nosql', str(path), validar=True)
            target = database.return_value.__getitem__.return_value
            target.bulk_write.assert_not_called()
            call_command('cargar_documentos_nosql', str(path))
            operation = target.bulk_write.call_args.args[0][0]
            self.assertEqual(operation._filter, {'_id': 'pref_1'})
            self.assertTrue(operation._upsert)

    def test_missing_mongo_parent_is_rejected(self):
        from rest_framework.exceptions import ValidationError as APIValidationError
        from .services import validate_document
        database = MagicMock()
        database.__getitem__.return_value.find_one.return_value = None
        with self.assertRaises(APIValidationError):
            validate_document('sustituciones_ofrecidas', dict(transaccion_id='missing',
                              producto_solicitado='A', producto_alternativo_ofrecido='B'), database)

    def test_plaintext_hash_is_rejected(self):
        from rest_framework.exceptions import ValidationError as APIValidationError
        from .services import validate_document
        with self.assertRaises(APIValidationError):
            validate_document('usuarios_empresas_roles', self.user_data())
