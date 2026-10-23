from types import SimpleNamespace as Obj
from unittest.mock import MagicMock, patch
from decimal import Decimal
from django.test import SimpleTestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate
from .customer_views import CustomerDocumentsView, ClaimResponseView
from .analytics_views import ProviderAnalyticsView


class CustomerFlowTests(SimpleTestCase):
    def request(self, method, data=None, role='Restaurante', path='/'):
        request = getattr(APIRequestFactory(), method)(path, data or {}, format='json')
        force_authenticate(request, user=Obj(pk=7, is_authenticated=True, rolid=Obj(nombrerol=role)))
        return request

    @patch('Tradconnect_no_sql.customer_views.company')
    def test_customer_cannot_spoof_owner(self, companies):
        companies.return_value = Obj(pk=10)
        response = CustomerDocumentsView.as_view()(self.request('post', {'cliente_empresa_id': '999'}), collection='incidencias_entregas')
        self.assertEqual(response.status_code, 400)

    @patch('Tradconnect_no_sql.customer_views.Pedido')
    @patch('Tradconnect_no_sql.customer_views.company')
    def test_foreign_order_rejected(self, companies, orders):
        owner = Obj(pk=10, razonsocial='Cliente')
        companies.return_value = owner
        orders.objects.filter.return_value.first.return_value = None
        response = CustomerDocumentsView.as_view()(self.request('post', {'pedido_id_sql': 123, 'tipo_incidencia': 'Entrega', 'tipo_reclamo': 'Tarde'}), collection='incidencias_entregas')
        self.assertEqual(response.status_code, 404)
        orders.objects.filter.assert_called_once_with(pk=123, restauranteid=owner.pk)

    @patch('Tradconnect_no_sql.customer_views.get_database')
    @patch('Tradconnect_no_sql.customer_views.company')
    def test_provider_cannot_respond_to_foreign_claim(self, company, database):
        company.return_value = Obj(pk=20)
        database.return_value.__getitem__.return_value.find_one.return_value = None
        response = ClaimResponseView.as_view()(self.request('patch', {'estado': 'Resuelta', 'respuesta_proveedor': 'Respuesta'}, role='Proveedor'), pk='foreign')
        self.assertEqual(response.status_code, 404)
        database.return_value.__getitem__.return_value.find_one.assert_called_once_with({'_id': 'foreign', 'proveedor_empresa_id': '20'})

    @patch('Tradconnect_no_sql.customer_views.get_database')
    @patch('Tradconnect_no_sql.customer_views.company')
    def test_list_filters_by_current_company(self, company, database):
        company.return_value = Obj(pk=20)
        collection = database.return_value.__getitem__.return_value
        collection.find.return_value.sort.return_value.skip.return_value.limit.return_value = []
        response = CustomerDocumentsView.as_view()(self.request('get'), collection='incidencias_entregas')
        self.assertEqual(response.status_code, 200)
        collection.find.assert_called_once_with({'cliente_empresa_id': '20'})

    def test_client_cannot_view_provider_analytics(self):
        response = ProviderAnalyticsView.as_view()(self.request('get'))
        self.assertEqual(response.status_code, 403)

    @patch('Tradconnect_no_sql.analytics_views.get_database')
    @patch('Tradconnect_no_sql.analytics_views.Moneda')
    @patch('Tradconnect_no_sql.analytics_views.Pedido')
    @patch('Tradconnect_no_sql.analytics_views.company')
    def test_analytics_totals_and_scope(self, company, orders, currencies, database):
        owner = Obj(pk=20); company.return_value = owner
        currencies.objects.values.return_value = [{'id': 1, 'nombremoneda': 'Cordoba'}]
        detail = Obj(cantidad=Decimal('2'), preciounitario=Decimal('10'), descuentoaplicado=Decimal('10'), productoid_id=3,
            subtotallinea=Decimal('18'), productoid=Obj(nombreproducto='Arroz', categoriaid_id=4, categoriaid=Obj(nombrecategoria='Granos')))
        order = Obj(totalneto=Decimal('20.70'), fechapedido=timezone.now(), restauranteid_id=9,
            restauranteid=Obj(razonsocial='Cliente', ruc='R'), estadopedidoid=Obj(estadonombre='Pendiente'), sqldetallepedido_set=MagicMock())
        order.restauranteid = '9'
        order.sqldetallepedido_set.all.return_value = [detail]
        orders.objects.filter.return_value.select_related.return_value.prefetch_related.return_value = [order]
        database.return_value.__getitem__.return_value.find.return_value = []
        database.return_value.__getitem__.return_value.count_documents.return_value = 0
        with patch('Tradconnect_no_sql.analytics_views.company_names', return_value={'9':'Cliente'}):
            response = ProviderAnalyticsView.as_view()(self.request('get', role='Proveedor'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['ventas'][0]['total_ventas'], Decimal('20.70'))
        self.assertEqual(response.data['productos'][0]['total_ingreso'], Decimal('18'))
        self.assertEqual(orders.objects.filter.call_args.kwargs['proveedorid'], owner.pk)
        self.assertEqual(orders.objects.filter.call_args.kwargs['monedaid_id'], 1)
