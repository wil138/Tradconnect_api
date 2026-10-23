from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from config.mongodb import get_database
from .models import SCHEMAS
from .services import (MONGO_REFERENCES, create_document, read_document,
                       schemas, validate_document)
from .views import DocumentView


class CollectionView(DocumentView):
    def get(self, request, collection):
        schemas(collection)
        try:
            limit = int(request.query_params.get('limit', 100))
            offset = int(request.query_params.get('offset', 0))
        except (ValueError, TypeError):
            raise ValidationError('limit y offset deben ser enteros.')
        if not 1 <= limit <= 500 or offset < 0:
            raise ValidationError('limit debe estar entre 1 y 500 y offset debe ser >= 0.')
        docs = get_database()[collection].find().sort('_id', 1).skip(offset).limit(limit)
        return Response({'limit': limit, 'offset': offset,
                         'results': [read_document(collection, doc) for doc in docs]})

    def post(self, request, collection):
        return Response(create_document(collection, request.data), status=201)


class ItemView(DocumentView):
    def get_item(self, collection, pk):
        schemas(collection)
        document = get_database()[collection].find_one({'_id': pk})
        if document is None:
            raise NotFound('Documento no encontrado.')
        return document

    def get(self, request, collection, pk):
        return Response(read_document(collection, self.get_item(collection, pk)))

    def put(self, request, collection, pk):
        self.get_item(collection, pk)
        document = validate_document(collection, request.data)
        document['_id'] = pk
        result = get_database()[collection].replace_one({'_id': pk}, document)
        if not result.matched_count:
            raise NotFound('Documento no encontrado.')
        return Response(read_document(collection, document))

    def patch(self, request, collection, pk):
        if not isinstance(request.data, dict):
            raise ValidationError('Se requiere un objeto JSON.')
        document = self.get_item(collection, pk)
        document.pop('_id')
        document.update(request.data)
        validated = validate_document(collection, document)
        validated['_id'] = pk
        result = get_database()[collection].replace_one({'_id': pk}, validated)
        if not result.matched_count:
            raise NotFound('Documento no encontrado.')
        return Response(read_document(collection, validated))

    def delete(self, request, collection, pk):
        self.get_item(collection, pk)
        database = get_database()
        for field, target in MONGO_REFERENCES.items():
            if target == collection:
                for child, (schema, _) in SCHEMAS.items():
                    if field in schema.model_fields and database[child].find_one({field: pk}, {'_id': 1}):
                        raise ValidationError('El documento tiene referencias; elimina primero sus dependientes.')
        database[collection].delete_one({'_id': pk})
        return Response(status=204)


class SchemaView(DocumentView):
    def get(self, request):
        return Response({name: schema.model_json_schema() for name, (schema, _) in SCHEMAS.items()})
