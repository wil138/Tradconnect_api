from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, ValidationError
from django.core.exceptions import ImproperlyConfigured
from pymongo.errors import PyMongoError

from config.mongodb import get_database
from TradConnect.models import Empresa
from .views import DocumentView, MongoUnavailable


def dump_order_lists(company_id):
    """Mantiene el formato del dump anterior con el mismo alcance por empresa."""
    try:
        collection = get_database()['pedidos_web']
        return {
            name: [MyOrdersView.representation(doc) for doc in collection.find({field: company_id}).sort([('fechapedido', -1), ('_id', -1)])]
            for name, field in (('pedidos_comprador', 'restauranteid'), ('pedidos_proveedor', 'proveedorid'))
        }
    except (PyMongoError, ImproperlyConfigured):
        raise MongoUnavailable()


class MyOrdersView(DocumentView):
    permission_classes = [IsAuthenticated]

    def company_ids(self, request):
        return list(Empresa.objects.filter(usuarioid=request.user).values_list('pk', flat=True))

    def scope(self, request):
        ids = self.company_ids(request)
        return {'$or': [{'restauranteid': {'$in': ids}}, {'proveedorid': {'$in': ids}}]}

    @staticmethod
    def representation(document):
        return {key: value for key, value in document.items() if key not in ('_id', 'sincronizado_en')}

    def get(self, request, pk=None):
        scope = self.scope(request)
        collection = get_database()['pedidos_web']
        if pk is not None:
            document = collection.find_one({'$and': [scope, {'_id': pk}]})
            if document is None:
                raise NotFound('Pedido no encontrado.')
            return Response(self.representation(document))
        try:
            limit = int(request.query_params.get('limit', 100))
            offset = int(request.query_params.get('offset', 0))
        except (ValueError, TypeError):
            raise ValidationError('limit y offset deben ser enteros.')
        if not 1 <= limit <= 500 or offset < 0:
            raise ValidationError('limit debe estar entre 1 y 500 y offset debe ser >= 0.')
        documents = collection.find(scope).sort([('fechapedido', -1), ('_id', -1)]).skip(offset).limit(limit)
        return Response({'limit': limit, 'offset': offset,
                         'results': [self.representation(document) for document in documents]})
