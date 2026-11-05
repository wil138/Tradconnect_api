from unittest.mock import patch
from django.test import SimpleTestCase, override_settings
from django.urls import reverse
from django.core.exceptions import ImproperlyConfigured
from config.connections import check_sql, check_mongo
from config.connection_settings import load_database_connections, parse_sqlserver_connection_string


class DatabaseConnectionSettingsTests(SimpleTestCase):
    def test_sqlserver_odbc_connection_string_parses_required_fields(self):
        result=parse_sqlserver_connection_string(
            'Server=tcp:db.example,1433;Initial Catalog=TradConnect;'
            'User ID=api-user;Password={p;{word}}};Encrypt=True;'
        )
        self.assertEqual(result,{
            'HOST':'tcp:db.example,1433',
            'NAME':'TradConnect',
            'USER':'api-user',
            'PASSWORD':'p;{word}',
        })

    def test_cloud_profile_uses_separate_environment_values(self):
        result=load_database_connections({
            'DATABASE_PROFILE':'cloud',
            'CLOUD_SQLSERVER_CONNECTION_STRING':(
                'Server=tcp:db.example,1433;Initial Catalog=TradConnect;'
                'User ID=api-user;Password=secret'
            ),
            'CLOUD_MONGODB_URI':'mongodb://cloud.example',
            'CLOUD_MONGODB_DATABASE':'tradconnect_cloud',
        },{'SQLSERVER_HOST':r'.\WIL','MONGODB_URI':'mongodb://localhost'})
        self.assertEqual(result['profile'],'cloud')
        self.assertEqual(result['sql']['HOST'],'tcp:db.example,1433')
        self.assertEqual(result['mongodb_uri'],'mongodb://cloud.example')
        self.assertEqual(result['mongodb_database'],'tradconnect_cloud')

    def test_cloud_profile_requires_its_own_connections(self):
        with self.assertRaisesMessage(ImproperlyConfigured,'CLOUD_SQLSERVER_CONNECTION_STRING'):
            load_database_connections({'DATABASE_PROFILE':'cloud'},{
                'SQLSERVER_HOST':r'.\WIL',
                'MONGODB_URI':'mongodb://localhost',
            })


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
