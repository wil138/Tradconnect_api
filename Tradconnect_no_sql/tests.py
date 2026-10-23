from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.test import SimpleTestCase, override_settings
from rest_framework.test import APIRequestFactory, force_authenticate

from config.mongodb import get_database
from TradConnect.models import Categoria, Producto
from .projections import DocumentModel, document_value, get_document_models
from .views import DocumentList


class IntegrationTests(SimpleTestCase):
    def test_models_and_values(self):
        self.assertNotIn('usuario', get_document_models())
        self.assertEqual(document_value(Decimal('12.30')), '12.30')
        self.assertEqual(document_value(date(2026, 1, 1)), '2026-01-01')
        product = Producto(id=7, empresaid_id=2, categoriaid_id=3,
                           unidadmedidaid_id=1, precioventa=Decimal('12.30'))
        document = DocumentModel(Producto).serialize(product)
        self.assertEqual(document['_id'], 7)
        self.assertEqual(document['empresaid'], 2)

    def test_old_routes_still_resolve(self):
        from django.urls import resolve
        self.assertEqual(resolve('/api/productos/').url_name, 'producto-list')
        self.assertEqual(resolve('/api/auth/login/').url_name, 'auth-login')
        self.assertEqual(resolve('/api/nosql/producto/').url_name, 'nosql-list')

    @override_settings(MONGODB_URI=None)
    def test_missing_mongo_is_503_for_admin(self):
        request = APIRequestFactory().get('/api/nosql/producto/')
        force_authenticate(request, SimpleNamespace(is_authenticated=True,
                           rolid=SimpleNamespace(nombrerol='Administrador')))
        self.assertEqual(DocumentList.as_view()(request, collection='producto').status_code, 503)

    def test_regular_user_cannot_read_all_companies(self):
        request = APIRequestFactory().get('/api/nosql/producto/')
        force_authenticate(request, SimpleNamespace(is_authenticated=True,
                           rolid=SimpleNamespace(nombrerol='Proveedor')))
        self.assertEqual(DocumentList.as_view()(request, collection='producto').status_code, 403)

    @patch('Tradconnect_no_sql.management.commands.cargar_nosql.get_document_models')
    def test_load_uses_upsert_and_preserves_ids(self, registry):
        model = MagicMock()
        model.sql_model.objects.using.return_value.order_by.return_value.iterator.return_value = [
            Categoria(id=5, nombrecategoria='Frutas')]
        model.serialize.return_value = {'_id': 5, 'id': 5, 'nombrecategoria': 'Frutas'}
        registry.return_value = {'categoria': model}
        call_command('cargar_nosql', coleccion=['categoria'], batch_size=1)
        operation = model.collection.bulk_write.call_args.args[0][0]
        self.assertEqual(operation._filter, {'_id': 5})
        self.assertTrue(operation._upsert)
