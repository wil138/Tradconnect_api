from types import SimpleNamespace
from unittest.mock import patch
from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory, force_authenticate
from .document_views import CollectionView, SchemaView

class CollectionAccessTests(SimpleTestCase):
    def request(self, role):
        request = APIRequestFactory().get('/api/nosql/esquemas/')
        force_authenticate(request, user=SimpleNamespace(is_authenticated=True, rolid=SimpleNamespace(nombrerol=role)))
        return request

    @patch('Tradconnect_no_sql.document_views.get_database')
    def test_clients_and_providers_cannot_read_administrative_collections(self, database):
        for role in ['Restaurante', 'Proveedor']:
            with self.subTest(role=role):
                self.assertEqual(SchemaView.as_view()(self.request(role)).status_code, 403)
                self.assertEqual(CollectionView.as_view()(self.request(role), collection='usuarios_empresas_roles').status_code, 403)
        database.assert_not_called()

    def test_administrator_receives_all_thirteen_schemas(self):
        response = SchemaView.as_view()(self.request('Administrador'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 13)
