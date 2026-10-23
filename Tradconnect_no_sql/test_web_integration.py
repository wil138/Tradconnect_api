from types import SimpleNamespace
from unittest.mock import patch
from django.test import SimpleTestCase
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate
from .document_views import SchemaView
from .models import SCHEMAS
from TradConnect.views import AuthViewSet


class WebIntegrationTests(SimpleTestCase):
    def user(self, role):
        return SimpleNamespace(is_authenticated=True, rolid=SimpleNamespace(nombrerol=role))

    def test_schemas_require_admin(self):
        request = APIRequestFactory().get('/api/nosql/esquemas/')
        force_authenticate(request, user=self.user('Restaurante'))
        self.assertEqual(SchemaView.as_view()(request).status_code, 403)

    def test_admin_gets_all_form_schemas_without_database(self):
        request = APIRequestFactory().get('/api/nosql/esquemas/')
        force_authenticate(request, user=self.user('Administrador'))
        response = SchemaView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.data), set(SCHEMAS))
        self.assertIn('puntuacion', response.data['evaluaciones_proveedores']['properties'])

    def test_snapshot_uses_authenticated_user_without_password(self):
        request = APIRequestFactory().get('/api/auth/my-data/')
        user = self.user('Restaurante')
        force_authenticate(request, user=user)
        with patch.object(AuthViewSet, 'build_snapshot', return_value=Response({'usuario': {}})) as build:
            response = AuthViewSet.as_view({'get': 'my_data'})(request)
        self.assertEqual(response.status_code, 200)
        build.assert_called_once_with(user, 'sql')
        self.assertNotIn('tokens', response.data)

    def test_snapshot_rejects_unknown_source(self):
        request = APIRequestFactory().get('/api/auth/my-data/?fuente_pedidos=invalid')
        force_authenticate(request, user=self.user('Restaurante'))
        self.assertEqual(AuthViewSet.as_view({'get': 'my_data'})(request).status_code, 400)
