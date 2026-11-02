from types import SimpleNamespace
from unittest.mock import patch
from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory, force_authenticate
from .analytics_views import CustomerAnalyticsView, ProviderAnalyticsView


class AnalyticsExportScopeTests(SimpleTestCase):
    def request(self, role):
        request = APIRequestFactory().get('/?start=2026-01-01&end=2026-02-01&moneda=1')
        force_authenticate(request, user=SimpleNamespace(is_authenticated=True,
            rolid=SimpleNamespace(nombrerol=role)))
        return request

    def test_provider_cannot_use_customer_analytics(self):
        response = CustomerAnalyticsView.as_view()(self.request('Proveedor'))
        self.assertEqual(response.status_code, 403)

    @patch('Tradconnect_no_sql.analytics_views.get_database')
    @patch('Tradconnect_no_sql.analytics_views.Moneda')
    @patch('Tradconnect_no_sql.analytics_views.Pedido')
    @patch('Tradconnect_no_sql.analytics_views.company')
    def test_customer_scope_uses_own_purchases_and_selected_currency(self, company, orders, currencies, database):
        owner = SimpleNamespace(pk=27)
        company.return_value = owner
        currencies.objects.values.return_value = [{'id': 1, 'nombremoneda': 'Cordoba'}]
        orders.objects.filter.return_value.select_related.return_value.prefetch_related.return_value = []
        database.return_value.__getitem__.return_value.find.return_value = []
        database.return_value.__getitem__.return_value.count_documents.return_value = 0
        with patch('Tradconnect_no_sql.analytics_views.company_names',return_value={}):
            response = CustomerAnalyticsView.as_view()(self.request('Restaurante'))
        self.assertEqual(response.status_code, 200)
        company.assert_called_once_with(company.call_args.args[0], provider=False)
        filters = orders.objects.filter.call_args.kwargs
        self.assertEqual(filters['restauranteid'], owner.pk)
        self.assertNotIn('proveedorid', filters)
        self.assertEqual(filters['monedaid_id'], 1)
        self.assertEqual(filters['fechapedido__date__gte'].isoformat(), '2026-01-01')
        self.assertEqual(response.data['ventas'], [])
        scope = database.return_value.__getitem__.return_value.find.call_args.args[0]
        self.assertEqual(scope['cliente_empresa_id'], '27')
