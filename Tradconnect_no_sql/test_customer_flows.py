from types import SimpleNamespace as Obj
from unittest.mock import MagicMock, patch
from decimal import Decimal
from django.test import SimpleTestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.exceptions import NotFound, PermissionDenied
from pydantic import ValidationError as PydanticValidationError
from .customer_views import (
    CustomerDocumentsView, ClaimResponseView, CommentInteractionsView,
    company_collection_query,
)
from .analytics_views import ProviderAnalyticsView
from .models import InteraccionComentarioCreate


class CustomerFlowTests(SimpleTestCase):
    def request(self, method, data=None, role='Restaurante', path='/'):
        request = getattr(APIRequestFactory(), method)(path, data or {}, format='json')
        force_authenticate(request, user=Obj(pk=7, is_authenticated=True, rolid=Obj(nombrerol=role)))
        return request

    def comment_request(self, method, data=None, role='Proveedor'):
        request = getattr(APIRequestFactory(), method)('/api/nosql/mi-empresa/comentarios/review-1/interacciones/', data or {}, format='json')
        user = Obj(
            pk='user-20',
            is_authenticated=True,
            rolid=Obj(nombrerol=role),
            document={'nombre_usuario': 'Ana'},
        )
        force_authenticate(request, user=user)
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

    @patch('Tradconnect_no_sql.customer_views.get_database')
    @patch('Tradconnect_no_sql.customer_views.company')
    def test_preference_children_are_scoped_through_owned_business_preferences(self, company, get_database):
        company.return_value = Obj(pk=20)
        db = get_database.return_value
        preferences = MagicMock()
        preferences.find.return_value = [{'_id': 'pref-owned'}]
        child_collection = MagicMock()
        child_collection.find.return_value.sort.return_value.skip.return_value.limit.return_value = []
        db.__getitem__.side_effect = lambda name: {
            'preferencias_negocio': preferences,
            'preferencias_categorias': child_collection,
        }[name]

        response = CustomerDocumentsView.as_view()(
            self.request('get'),
            collection='preferencias_categorias',
        )

        self.assertEqual(response.status_code, 200)
        preferences.find.assert_called_once_with({'empresa_id': '20'}, {'_id': 1})
        child_collection.find.assert_called_once_with({'preferencia_id': {'$in': ['pref-owned']}})

    @patch('Tradconnect_no_sql.customer_views.get_database')
    @patch('Tradconnect_no_sql.customer_views.company')
    def test_incident_evidence_is_scoped_through_company_incidents(self, company, get_database):
        company.return_value = Obj(pk=20)
        db = get_database.return_value
        incidents = MagicMock()
        incidents.find.return_value = [{'_id': 'incident-owned'}]
        evidence = MagicMock()
        evidence.find.return_value.sort.return_value.skip.return_value.limit.return_value = []
        db.__getitem__.side_effect = lambda name: {
            'incidencias_entregas': incidents,
            'evidencias_incidencia': evidence,
        }[name]

        response = CustomerDocumentsView.as_view()(
            self.request('get'),
            collection='evidencias_incidencia',
        )

        self.assertEqual(response.status_code, 200)
        incidents.find.assert_called_once_with({'cliente_empresa_id': '20'}, {'_id': 1})
        evidence.find.assert_called_once_with({'incidencia_id': {'$in': ['incident-owned']}})

    @patch('Tradconnect_no_sql.customer_views.get_database')
    @patch('Tradconnect_no_sql.customer_views.company')
    def test_substitutions_are_scoped_through_provider_transactions(self, company, get_database):
        company.return_value = Obj(pk=30)
        db = get_database.return_value
        transactions = MagicMock()
        transactions.find.return_value = [{'_id': 'transaction-owned'}]
        substitutions = MagicMock()
        substitutions.find.return_value.sort.return_value.skip.return_value.limit.return_value = []
        db.__getitem__.side_effect = lambda name: {
            'transacciones_no_exitosas': transactions,
            'sustituciones_ofrecidas': substitutions,
        }[name]

        response = CustomerDocumentsView.as_view()(
            self.request('get', role='Proveedor'),
            collection='sustituciones_ofrecidas',
        )

        self.assertEqual(response.status_code, 200)
        transactions.find.assert_called_once_with({'proveedor_empresa_id': '30'}, {'_id': 1})
        substitutions.find.assert_called_once_with({'transaccion_id': {'$in': ['transaction-owned']}})

    def test_company_query_rejects_identity_collection_and_provider_preferences(self):
        with self.assertRaises(NotFound):
            company_collection_query(MagicMock(), 'usuarios_empresas_roles', '20', False)
        with self.assertRaises(PermissionDenied):
            company_collection_query(MagicMock(), 'preferencias_negocio', '30', True)

    @patch('Tradconnect_no_sql.customer_views.get_database')
    @patch('Tradconnect_no_sql.customer_views.company')
    def test_company_comments_include_named_replies_from_both_parties(self, company, get_database):
        company.return_value = Obj(pk=20)
        db = get_database.return_value
        comments = db.__getitem__.return_value
        comment = {
            '_id': 'review-1', 'pedido_id_sql': 5, 'cliente_empresa_id': '20',
            'cliente_nombre': 'Restaurante', 'proveedor_empresa_id': '30',
            'proveedor_nombre': 'Proveedor', 'opinion_libre': 'Buen servicio',
            'calificacion': 5, 'fecha': timezone.now(),
        }
        unrelated_comment = {
            '_id': 'review-2', 'pedido_id_sql': 6, 'cliente_empresa_id': '20',
            'cliente_nombre': 'Restaurante', 'proveedor_empresa_id': '90',
            'proveedor_nombre': 'Otro proveedor', 'opinion_libre': 'Buen servicio',
            'calificacion': 5, 'fecha': timezone.now(),
        }
        comments.find.return_value.sort.return_value.skip.return_value.limit.return_value = [comment, unrelated_comment]
        interactions = MagicMock()
        interactions.find.return_value.sort.return_value = [
            {'_id': 'reply-1', 'comentario_id': 'review-1', 'fecha': timezone.now(),
             'tipo': 'Respuesta', 'mensaje': 'Gracias', 'usuario_id': 'user-30'},
            {'_id': 'reply-2', 'comentario_id': 'review-2', 'fecha': timezone.now(),
             'tipo': 'Respuesta', 'mensaje': 'No pertenece a este proveedor', 'usuario_id': 'user-30'},
        ]
        get_database.return_value.__getitem__.side_effect = lambda name: {
            'comentarios_post_compra': comments,
            'interacciones_comentario': interactions,
        }[name]
        with patch('Tradconnect_no_sql.customer_views.users') as user_collection:
            user_collection.return_value.find.return_value = [
                {'usuario_id': 'user-30', 'empresa_id': '30', 'nombre_usuario': 'Luis'},
            ]
            response = CustomerDocumentsView.as_view()(
                self.request('get', role='Proveedor'),
                collection='comentarios_post_compra',
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['results'][0]['interacciones'][0]['usuario_nombre'], 'Luis')
        self.assertEqual(response.data['results'][1]['interacciones'], [])
        query = user_collection.return_value.find.call_args.args[0]
        self.assertEqual(query['usuario_id']['$in'], ['user-30'])
        self.assertEqual(set(query['empresa_id']['$in']), {'20', '30', '90'})

    @patch('Tradconnect_no_sql.customer_views.get_database')
    @patch('Tradconnect_no_sql.customer_views.company')
    def test_comment_interaction_cannot_be_read_by_a_nonparticipant(self, company, get_database):
        company.return_value = Obj(pk=99)
        get_database.return_value.__getitem__.return_value.find_one.return_value = None

        response = CommentInteractionsView.as_view()(
            self.comment_request('get', role='Proveedor'),
            pk='review-1',
        )

        self.assertEqual(response.status_code, 404)
        get_database.return_value.__getitem__.return_value.find_one.assert_called_once_with({
            '_id': 'review-1',
            'proveedor_empresa_id': '99',
        })

    @patch('Tradconnect_no_sql.customer_views.validate_document')
    @patch('Tradconnect_no_sql.customer_views.get_database')
    @patch('Tradconnect_no_sql.customer_views.company')
    def test_comment_participant_can_add_a_reply_to_the_existing_mongo_thread(self, company, get_database, validate):
        company.return_value = Obj(pk=30)
        db = get_database.return_value
        comments = MagicMock()
        comments.find_one.return_value = {
            '_id': 'review-1',
            'proveedor_empresa_id': '30',
            'cliente_empresa_id': '20',
        }
        interactions = MagicMock()
        db.__getitem__.side_effect = lambda name: {
            'comentarios_post_compra': comments,
            'interacciones_comentario': interactions,
        }[name]
        validate.side_effect = lambda collection, payload: payload

        response = CommentInteractionsView.as_view()(
            self.comment_request('post', {'mensaje': '  Gracias por compartir tu experiencia.  '}),
            pk='review-1',
        )

        self.assertEqual(response.status_code, 201)
        inserted = interactions.insert_one.call_args.args[0]
        self.assertEqual(inserted['comentario_id'], 'review-1')
        self.assertEqual(inserted['tipo'], 'Respuesta')
        self.assertEqual(inserted['mensaje'], 'Gracias por compartir tu experiencia.')
        self.assertEqual(inserted['usuario_id'], 'user-20')
        self.assertEqual(response.data['usuario_nombre'], 'Ana')
        validate.assert_called_once_with('interacciones_comentario', inserted)

    def test_comment_interactions_reject_blank_or_oversized_messages(self):
        with self.assertRaises(PydanticValidationError):
            InteraccionComentarioCreate.model_validate({
                'comentario_id': 'review-1', 'fecha': timezone.now(),
                'tipo': 'Respuesta', 'mensaje': '  ', 'usuario_id': 'user-1',
            })
        with self.assertRaises(PydanticValidationError):
            InteraccionComentarioCreate.model_validate({
                'comentario_id': 'review-1', 'fecha': timezone.now(),
                'tipo': 'Respuesta', 'mensaje': 'x' * 2001, 'usuario_id': 'user-1',
            })

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
