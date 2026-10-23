from unittest.mock import patch
from django.test import SimpleTestCase, override_settings
from django.urls import reverse
from config.connections import check_sql, check_mongo


class ConnectionViewsTests(SimpleTestCase):
    def test_original_home_still_opens_swagger(self):
        self.assertRedirects(self.client.get('/'),'/swagger/',fetch_redirect_response=False)

    def test_public_configuration_uses_central_named_routes(self):
        response=self.client.get('/api/configuracion/',HTTP_HOST='localhost:8000')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.data['api_base_url'],'http://localhost:8000/api')
        self.assertEqual(response.data['connections_url'],'http://localhost:8000/api/conexiones/')
        self.assertEqual(response.data['login_url'],'http://localhost:8000'+reverse('auth-login'))
        self.assertNotIn('MONGODB_URI',str(response.data))
        self.assertEqual(response['Cache-Control'],'no-store')

    def test_visualization_page_does_not_query_databases(self):
        response=self.client.get('/conexiones/')
        self.assertContains(response,'data-endpoint="/api/conexiones/"')
        self.assertContains(response,'/static/config/connections.js')
        self.assertContains(response,'/swagger/')

    @patch('config.connections.check_mongo',return_value={'connected':True,'ready':True,'message':'ok'})
    @patch('config.connections.check_sql',return_value={'connected':True,'ready':True,'message':'ok'})
    def test_both_connected_is_200(self,sql,mongo):
        response=self.client.get('/api/conexiones/')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.data['status'],'ok')

    @patch('config.connections.check_mongo',return_value={'connected':False,'ready':False,'message':'No disponible'})
    @patch('config.connections.check_sql',return_value={'connected':True,'ready':True,'message':'ok'})
    def test_failure_is_503_with_available_links(self,sql,mongo):
        response=self.client.get('/api/conexiones/')
        self.assertEqual(response.status_code,503)
        self.assertEqual(response.data['status'],'degraded')
        self.assertIn('swagger_url',response.data['links'])

    @patch('config.connections.connection.copy',side_effect=RuntimeError('password=private-value'))
    def test_sql_errors_do_not_expose_credentials(self,copy):
        result=check_sql()
        self.assertFalse(result['ready'])
        self.assertNotIn('private-value',str(result))

    @override_settings(MONGODB_URI='mongodb://example.invalid')
    @patch('config.connections.get_database',side_effect=RuntimeError('secret-user:secret-password'))
    def test_mongo_errors_do_not_expose_credentials(self,database):
        result=check_mongo()
        self.assertFalse(result['ready'])
        self.assertNotIn('secret-password',str(result))

    @override_settings(MONGODB_URI='mongodb://example.invalid')
    @patch('config.connections.get_database')
    def test_mongo_wrong_database_is_not_reported_ready(self,database):
        database.return_value.list_collection_names.return_value=[]
        result=check_mongo()
        self.assertTrue(result['connected'])
        self.assertFalse(result['ready'])
