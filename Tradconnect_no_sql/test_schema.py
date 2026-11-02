import json

from django.test import SimpleTestCase

from TradConnect.urls import router, auth_routes
from .models import SCHEMAS


class SwaggerCompatibilityTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Consulta el endpoint real de documentación; no permite acceso a bases.
        response = cls.client_class().get('/swagger.json/', HTTP_ACCEPT='application/json')
        if response.status_code != 200:
            raise AssertionError(f'Swagger devolvió {response.status_code}')
        cls.schema = json.loads(response.content)
        cls.paths = cls.schema['paths']

    def test_all_sql_router_methods_are_documented(self):
        for prefix, viewset, _ in router.registry:
            for path, actions in ((f'/{prefix}/', ('list', 'create')),
                                  (f'/{prefix}/{{id}}/', ('retrieve', 'update', 'partial_update', 'destroy'))):
                methods = {'list': 'get', 'create': 'post', 'retrieve': 'get',
                           'update': 'put', 'partial_update': 'patch', 'destroy': 'delete'}
                for action in actions:
                    if hasattr(viewset, action):
                        with self.subTest(path=path, method=methods[action]):
                            self.assertIn(methods[action], self.paths[path])
                            self.assertTrue(self.paths[path][methods[action]]['tags'][0].startswith('SQL Server /'))

    def test_all_auth_and_custom_actions_are_documented(self):
        for route in auth_routes:
            path = '/' + str(route.pattern)
            for method in route.callback.actions:
                self.assertIn(method, self.paths[path])
        self.assertIn('put', self.paths['/pedidos/{id}/update_status/'])
        for action in ('summary', 'recent_orders', 'sales_chart'):
            self.assertIn('get', self.paths[f'/dashboard/{action}/'])

    def test_all_mongo_crud_methods_are_documented(self):
        for collection in SCHEMAS:
            path = f'/nosql/{collection}/'
            for method in ('get', 'post'):
                self.assertIn(method, self.paths[path])
                self.assertEqual(self.paths[path][method]['tags'], [f'MongoDB / {collection}'])
            for method in ('get', 'put', 'patch', 'delete'):
                self.assertIn(method, self.paths[path + '{id}/'])
        self.assertIn('get', self.paths['/nosql/mis-pedidos/'])

    def test_both_sources_are_visible_without_authentication(self):
        self.assertEqual(self.schema['basePath'], '/api')
        self.assertTrue(self.schema['tags'][0]['name'].startswith('SQL Server /'))
        self.assertTrue(any(tag['name'].startswith('MongoDB /') for tag in self.schema['tags']))
        self.assertIn('/productos/', self.paths)
        self.assertIn('/nosql/preferencias_negocio/', self.paths)

    def test_swagger_ui_is_available(self):
        response = self.client.get('/swagger/')
        self.assertContains(response, 'SQL Server + MongoDB')
