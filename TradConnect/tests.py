from decimal import Decimal
from unittest.mock import patch

from django.db import DatabaseError
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from django.test import RequestFactory, SimpleTestCase
from django.db.models import CharField, ForeignKey
from rest_framework.exceptions import AuthenticationFailed

from config import connections as connection_views
from TradConnect.errors import api_exception_handler
from .identities import Principal, company_names, user_data
from .sql_models import SqlDetallepedido, SqlPedido, SqlProducto, SqlSucursal
from .hybrid_serializers import DetailSerializer


class ApiHealthTests(SimpleTestCase):
    def setUp(self):
        self.request = RequestFactory().get(
            '/',
            HTTP_HOST='127.0.0.1:8001',
        )

    def test_api_configuration_returns_the_request_api_origin(self):
        response = connection_views.ConfigurationView.as_view()(self.request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['api_base_url'], 'http://127.0.0.1:8001/api')

    @patch('config.connections.check_mongo', return_value={
        'connected': True, 'ready': True, 'message': 'ready',
    })
    @patch('config.connections.check_sql', return_value={
        'connected': True, 'ready': True, 'message': 'ready',
    })
    def test_connection_status_reports_ready_sql_and_mongodb(self, check_sql, check_mongo):
        response = connection_views.ConnectionsView.as_view()(self.request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'ok')
        self.assertTrue(response.data['databases']['sql']['ready'])
        self.assertTrue(response.data['databases']['mongodb']['ready'])
        check_sql.assert_called_once_with()
        check_mongo.assert_called_once_with()

    @patch('config.connections.check_mongo', return_value={
        'connected': True, 'ready': True, 'message': 'ready',
    })
    @patch('config.connections.check_sql', return_value={
        'connected': True, 'ready': False, 'message': 'missing tables',
    })
    def test_connection_status_reports_a_degraded_database(self, check_sql, check_mongo):
        response = connection_views.ConnectionsView.as_view()(self.request)

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data['status'], 'degraded')
        self.assertFalse(response.data['databases']['sql']['ready'])
        check_sql.assert_called_once_with()
        check_mongo.assert_called_once_with()


class DatabaseSchemaAlignmentTests(SimpleTestCase):
    def test_company_identifiers_match_the_string_columns(self):
        self.assertIsInstance(SqlProducto._meta.get_field('empresaid'), CharField)
        self.assertIsInstance(SqlSucursal._meta.get_field('empresaid'), CharField)
        self.assertEqual(SqlProducto._meta.get_field('empresaid').column, 'EmpresaId')
        self.assertEqual(SqlSucursal._meta.get_field('empresaid').column, 'EmpresaId')

    def test_order_and_detail_fields_match_the_current_sql_schema(self):
        self.assertIsInstance(SqlPedido._meta.get_field('restauranteid'), CharField)
        self.assertIsInstance(SqlPedido._meta.get_field('proveedorid'), CharField)
        self.assertEqual(SqlPedido._meta.get_field('sucursaloriginalid').column, 'SucursalOriginalId')
        self.assertIsInstance(SqlPedido._meta.get_field('estadopedidoid'), ForeignKey)
        self.assertEqual(SqlDetallepedido._meta.get_field('montodescuento').column, 'MontoDescuento')
        self.assertEqual(SqlDetallepedido._meta.get_field('subtotallinea').column, 'SubtotalLinea')

    def test_discount_percentage_is_derived_from_the_stored_discount_amount(self):
        detail = SqlDetallepedido(
            preciounitario=Decimal('10.00'),
            cantidad=Decimal('2.00'),
            montodescuento=Decimal('3.00'),
        )

        self.assertEqual(
            DetailSerializer().get_descuentoaplicado(detail),
            15.0,
        )


class IdentityDataTests(SimpleTestCase):
    def test_principal_rejects_missing_identity_fields_without_a_server_error(self):
        with self.assertRaises(AuthenticationFailed):
            Principal({'usuario_id': 'user-1', 'nombre_rol': None})

        with self.assertRaises(AuthenticationFailed):
            Principal({'nombre_rol': 'Cliente'})

    def test_user_display_name_falls_back_to_email_when_the_name_is_missing(self):
        principal = Principal({
            'usuario_id': 'user-1',
            'nombre_rol': 'Cliente',
            'estado_usuario': True,
            'estado_rol': True,
            'nombre_usuario': None,
            'correo': '  cliente@example.com  ',
        })

        data = user_data(principal)

        self.assertEqual(data['nombreusuario'], 'cliente@example.com')
        self.assertEqual(data['correoelectronico'], 'cliente@example.com')
        self.assertEqual(data['telefono'], '')

    @patch('TradConnect.identities.users')
    def test_company_names_omit_null_and_blank_database_values(self, users):
        users.return_value.find.return_value = [
            {'empresa_id': 'emp-1', 'razon_social': None},
            {'empresa_id': 'emp-2', 'razon_social': '   '},
            {'empresa_id': 'emp-3', 'razon_social': ' Restaurante Central '},
        ]

        self.assertEqual(company_names(['emp-1', 'emp-2', 'emp-3']), {'emp-3': 'Restaurante Central'})


class ApiDatabaseExceptionTests(SimpleTestCase):
    @patch('TradConnect.errors.logger.exception')
    def test_database_errors_return_a_controlled_service_unavailable_response(self, log_error):
        response = api_exception_handler(DatabaseError('table missing'), {})

        self.assertEqual(response.status_code, 503)
        self.assertIn('detail', response.data)
        log_error.assert_called_once()

    @patch('TradConnect.errors.logger.exception')
    def test_integrity_errors_return_a_conflict_response(self, log_error):
        response = api_exception_handler(IntegrityError('constraint violation'), {})

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data['code'], 'database_conflict')
        log_error.assert_called_once()

    def test_missing_records_return_not_found(self):
        response = api_exception_handler(ObjectDoesNotExist(), {})

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data['code'], 'not_found')

    @patch('TradConnect.errors.exception_handler', return_value=None)
    def test_non_database_errors_keep_the_default_drf_handling(self, default_handler):
        error = ValueError('invalid value')

        self.assertIsNone(api_exception_handler(error, {}))
        default_handler.assert_called_once_with(error, {})
