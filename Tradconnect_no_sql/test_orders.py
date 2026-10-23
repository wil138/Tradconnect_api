from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings
from rest_framework.test import APIRequestFactory, force_authenticate
from pymongo.errors import ServerSelectionTimeoutError

from TradConnect.models import Pedido, Detallepedido
from TradConnect.views import PedidoViewSet
from .order_sync import schedule_order_sync, sync_order
from .order_views import MyOrdersView
from .signals import order_changed
from .order_views import dump_order_lists
from .management.commands.sincronizar_pedidos import Command


class OrderSyncTests(SimpleTestCase):
    @patch('Tradconnect_no_sql.order_views.get_database')
    def test_dump_scopes_each_list_and_removes_internal_metadata(self, database):
        collection = database.return_value['pedidos_web']
        collection.find.return_value.sort.return_value = [{'_id': 7, 'id': 7, 'sincronizado_en': 'now'}]
        result = dump_order_lists(2)
        self.assertEqual(result['pedidos_comprador'], [{'id': 7}])
        self.assertEqual([call.args[0] for call in collection.find.call_args_list],
                         [{'restauranteid': 2}, {'proveedorid': 2}])

    @patch('Tradconnect_no_sql.management.commands.sincronizar_pedidos.Pedido.objects.filter')
    def test_verification_reports_orphaned_web_document_without_writing(self, orders):
        orders.return_value.first.return_value = None
        database = MagicMock()
        database.__getitem__.return_value.find.return_value = []
        database['pedidos_web'].find_one.return_value = {'_id': 7, 'id': 7}
        with patch('Tradconnect_no_sql.management.commands.sincronizar_pedidos.SOURCES', []):
            differences = Command().differences(7, database)
        self.assertEqual(differences, ['pedidos_web'])
        database['pedidos_web'].replace_one.assert_not_called()

    @override_settings(MONGODB_URI='mongodb://localhost')
    @patch('Tradconnect_no_sql.order_sync.transaction.on_commit')
    @patch('Tradconnect_no_sql.order_sync.sync_order')
    def test_sync_waits_for_commit(self, sync, on_commit):
        schedule_order_sync(7)
        sync.assert_not_called()
        callback = on_commit.call_args.args[0]
        callback()
        sync.assert_called_once_with(7)

    @override_settings(MONGODB_URI='mongodb://localhost')
    @patch('Tradconnect_no_sql.order_sync.transaction.on_commit')
    @patch('Tradconnect_no_sql.order_sync.sync_order', side_effect=ServerSelectionTimeoutError('private connection info'))
    def test_mongo_failure_after_commit_is_logged_without_raising(self, sync, on_commit):
        schedule_order_sync(7)
        with self.assertLogs('Tradconnect_no_sql.order_sync', level='ERROR') as logs:
            on_commit.call_args.args[0]()
        self.assertIn('--pedido 7', logs.output[0])
        self.assertNotIn('private connection info', logs.output[0])

    @override_settings(MONGODB_URI=None)
    @patch('Tradconnect_no_sql.order_sync.transaction.on_commit')
    def test_sql_works_without_mongo_configuration(self, on_commit):
        schedule_order_sync(7)
        on_commit.assert_not_called()

    @patch('Tradconnect_no_sql.signals.schedule_order_sync')
    def test_child_changes_sync_both_orders_when_reassigned(self, schedule):
        instance = SimpleNamespace(pk=9, pedidoid_id=7, _nosql_previous_order=6)
        order_changed(Detallepedido, instance, 'default')
        self.assertEqual([call.args[0] for call in schedule.call_args_list], [6, 7])

    @patch('Tradconnect_no_sql.order_sync.Pedido.objects.filter')
    def test_missing_sql_order_removes_all_projections(self, sql_filter):
        sql_filter.return_value.first.return_value = None
        database = MagicMock()
        sync_order(7, database)
        database['pedidos_web'].delete_one.assert_called_with({'_id': 7})
        database['detallepedido'].delete_many.assert_called_with({'pedidoid': 7})

    @patch('Tradconnect_no_sql.order_sync.web_document', return_value={'_id': 7, 'id': 7})
    @patch('Tradconnect_no_sql.order_sync.DocumentModel')
    @patch('Tradconnect_no_sql.order_sync.Historialestadopedido.objects.filter')
    @patch('Tradconnect_no_sql.order_sync.Detallepedido.objects.filter')
    @patch('Tradconnect_no_sql.order_sync.Pedido.objects.filter')
    def test_upsert_and_removed_children_reconciliation(self, orders, details, history, model, web):
        order = SimpleNamespace(pk=7)
        orders.return_value.first.return_value = order
        details.return_value.order_by.return_value.iterator.return_value = [SimpleNamespace(pk=8)]
        history.return_value.order_by.return_value.iterator.return_value = []
        model.return_value.serialize.return_value = {'id': 7}
        collections = {name: MagicMock() for name in ('pedido', 'detallepedido', 'historialestadopedido', 'pedidos_web')}
        sync_order(7, collections)
        collections['detallepedido'].delete_many.assert_called_once_with({'pedidoid': 7, '_id': {'$nin': [8]}})
        args = collections['pedidos_web'].replace_one.call_args
        self.assertEqual(args.args[0], {'_id': 7})
        self.assertTrue(args.kwargs['upsert'])
        self.assertIn('sincronizado_en', args.args[1])

    @patch('Tradconnect_no_sql.order_views.get_database')
    @patch('Tradconnect_no_sql.order_views.MyOrdersView.company_ids',return_value=[2,3])
    def test_read_is_scoped_to_authenticated_companies(self, companies, database):
        database.return_value.__getitem__.return_value.find_one.return_value = None
        user = SimpleNamespace(is_authenticated=True)
        request = APIRequestFactory().get('/api/nosql/mis-pedidos/99/')
        force_authenticate(request, user)
        response = MyOrdersView.as_view()(request, pk=99)
        self.assertEqual(response.status_code, 404)
        query = database.return_value['pedidos_web'].find_one.call_args.args[0]
        self.assertEqual(query, {'$and': [{'$or': [{'restauranteid': {'$in': [2, 3]}},
                                                               {'proveedorid': {'$in': [2, 3]}}]}, {'_id': 99}]})
        companies.assert_called_once()

    def test_anonymous_cannot_read_orders(self):
        response = MyOrdersView.as_view()(APIRequestFactory().get('/api/nosql/mis-pedidos/'))
        self.assertEqual(response.status_code, 401)

    @patch('TradConnect.views.transaction.set_rollback')
    @patch('TradConnect.views.Inventariobodega.objects.filter')
    @patch('TradConnect.views.Detallepedido.objects.filter')
    @patch('TradConnect.views.Historialestadopedido.objects.create')
    @patch('TradConnect.views.Estadopedido.objects.get')
    @patch('TradConnect.views.Empresa.objects.filter')
    def test_insufficient_stock_rolls_back_the_status_change(self, companies, states, history, details, inventory, rollback):
        company = SimpleNamespace(pk=1)
        companies.return_value.first.return_value = company
        states.return_value = SimpleNamespace(estadonombre='Completado')
        details.return_value = [SimpleNamespace(productoid=SimpleNamespace(nombreproducto='Arroz'), cantidad=5)]
        inventory.return_value.first.return_value = SimpleNamespace(stockdisponible=1)
        view = PedidoViewSet()
        view.get_object = MagicMock(return_value=SimpleNamespace(proveedorid=company, sucursalorigenid=1))
        request = SimpleNamespace(user=object(), data={'estado_id': 1})
        response = PedidoViewSet.update_status.__wrapped__(view, request, pk=7)
        self.assertEqual(response.status_code, 400)
        rollback.assert_called_once_with(True)
