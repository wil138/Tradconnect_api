from django.core.exceptions import ImproperlyConfigured
from pymongo.errors import PyMongoError
from rest_framework.exceptions import APIException, NotFound, ValidationError
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView
from .projections import get_document_models


class MongoUnavailable(APIException):
    status_code = 503
    default_detail = 'MongoDB no está disponible. Revisa su configuración y conexión.'


class IsAdministrator(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and
                    user.rolid.nombrerol.casefold() in ('admin', 'administrador'))


class DocumentView(APIView):
    # Estas proyecciones contienen datos de varias empresas.
    permission_classes = [IsAdministrator]

    def get_collection(self, name):
        model = get_document_models().get(name)
        if model is None:
            raise NotFound('Colección desconocida.')
        return model.collection

    def handle_exception(self, exc):
        if isinstance(exc, (PyMongoError, ImproperlyConfigured)):
            exc = MongoUnavailable()
        return super().handle_exception(exc)

    @staticmethod
    def representation(document):
        document.pop('_id', None)
        return document


class DocumentList(DocumentView):
    def get(self, request, collection):
        try:
            limit = int(request.query_params.get('limit', 100))
            offset = int(request.query_params.get('offset', 0))
        except (ValueError, TypeError):
            raise ValidationError('limit y offset deben ser enteros.')
        if not 1 <= limit <= 500 or offset < 0:
            raise ValidationError('limit debe estar entre 1 y 500; offset debe ser >= 0.')
        documents = self.get_collection(collection).find().sort('_id', 1).skip(offset).limit(limit)
        return Response({'limit': limit, 'offset': offset,
                         'results': [self.representation(doc) for doc in documents]})


class DocumentDetail(DocumentView):
    def get(self, request, collection, pk):
        document = self.get_collection(collection).find_one({'_id': pk})
        if document is None:
            raise NotFound('Documento no encontrado.')
        return Response(self.representation(document))
