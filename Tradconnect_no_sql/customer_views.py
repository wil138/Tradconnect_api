"""Operaciones de clientes y proveedores con alcance derivado del JWT."""
from uuid import uuid4
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from config.mongodb import get_database
from TradConnect.sql_models import SqlPedido as Pedido, SqlCategoria as Categoria
from TradConnect.identities import company as mongo_company, company_names
from .views import DocumentView
from .services import validate_document, read_document

COLLECTIONS = {'incidencias_entregas', 'evaluaciones_proveedores',
               'comentarios_post_compra', 'preferencias_negocio', 'necesidades_no_satisfechas'}


def company(request, provider=False):
    return mongo_company(request, provider)


class CustomerDocumentsView(DocumentView):
    permission_classes = [IsAuthenticated]

    def get(self, request, collection):
        if collection not in COLLECTIONS:
            raise NotFound()
        provider = request.user.rolid.nombrerol.casefold() == 'proveedor'
        owner = company(request, provider)
        if provider and collection not in {'incidencias_entregas', 'evaluaciones_proveedores', 'comentarios_post_compra'}:
            raise PermissionDenied()
        field = 'proveedor_empresa_id' if provider else ('empresa_id' if collection == 'preferencias_negocio' else 'cliente_empresa_id')
        try:
            offset = int(request.query_params.get('offset', 0))
        except ValueError:
            raise ValidationError('offset inv?lido.')
        if offset < 0:
            raise ValidationError('offset inv?lido.')
        docs = get_database()[collection].find({field: str(owner.pk)}).sort([('fecha_actualizacion' if collection == 'preferencias_negocio' else 'fecha', -1), ('_id', -1)]).skip(offset).limit(50)
        return Response({'results': [read_document(collection, doc) for doc in docs], 'offset': offset})

    def post(self, request, collection):
        if collection not in COLLECTIONS:
            raise NotFound()
        owner = company(request)
        if not isinstance(request.data, dict):
            raise ValidationError('Se requiere un objeto.')
        allowed = {
            'incidencias_entregas': {'pedido_id_sql', 'tipo_incidencia', 'tipo_reclamo'},
            'evaluaciones_proveedores': {'pedido_id_sql', 'calidad', 'tiempo_entrega', 'precio', 'atencion', 'comentario'},
            'comentarios_post_compra': {'pedido_id_sql', 'opinion_libre', 'calificacion'},
            'preferencias_negocio': {'horario_entrega_preferido'},
            'necesidades_no_satisfechas': {'insumo_buscado', 'cantidades_requeridas', 'unidad', 'categoria_id_sql'},
        }[collection]
        if set(request.data) - allowed:
            raise ValidationError('Se enviaron campos no permitidos.')
        payload = dict(request.data)
        if collection == 'preferencias_negocio':
            payload.update(empresa_id=str(owner.pk), usuario_id=str(request.user.pk), fecha_actualizacion=timezone.now())
        else:
            payload.update(cliente_empresa_id=str(owner.pk), cliente_nombre=owner.razonsocial, fecha=timezone.now())
            if collection != 'necesidades_no_satisfechas':
                try:
                    order_id = int(payload.get('pedido_id_sql'))
                except (ValueError, TypeError):
                    raise ValidationError('Selecciona un pedido válido.')
                order = Pedido.objects.filter(pk=order_id, restauranteid=owner.pk).first()
                if order is None:
                    raise NotFound('Pedido no encontrado para tu empresa.')
                payload.update(proveedor_empresa_id=str(order.proveedorid), proveedor_nombre=company_names([order.proveedorid]).get(order.proveedorid,'Proveedor'))
            if collection in {'incidencias_entregas', 'necesidades_no_satisfechas'}:
                payload['estado'] = 'Pendiente'
            if collection == 'evaluaciones_proveedores':
                try:
                    scores = [int(payload[key]) for key in ('calidad', 'tiempo_entrega', 'precio', 'atencion')]
                except (KeyError, TypeError, ValueError):
                    raise ValidationError('Completa las cuatro puntuaciones de 1 a 5.')
                payload['puntuacion'] = sum(scores) / 4
        db = get_database()
        document = validate_document(collection, payload, db)
        if collection == 'preferencias_negocio':
            scope={'empresa_id':str(owner.pk),'usuario_id':str(request.user.pk)}
            existing=db[collection].find_one(scope)
            document['_id']=existing['_id'] if existing else 'pref_'+str(owner.pk)+'_'+str(request.user.pk)
            db[collection].replace_one({'_id':document['_id']},document,upsert=True)
        else:
            document['_id'] = str(uuid4())
            db[collection].insert_one(document)
        return Response(read_document(collection, document), status=201)


class ClaimResponseView(DocumentView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        owner = company(request, provider=True)
        if not isinstance(request.data, dict) or set(request.data) != {'estado', 'respuesta_proveedor'}:
            raise ValidationError('Env?a estado y respuesta_proveedor.')
        if not isinstance(request.data['respuesta_proveedor'], str) or not request.data['respuesta_proveedor'].strip():
            raise ValidationError('Escribe una respuesta al cliente.')
        collection = get_database()['incidencias_entregas']
        scope = {'_id': pk, 'proveedor_empresa_id': str(owner.pk)}
        document = collection.find_one(scope)
        if document is None:
            raise NotFound('Reclamo no encontrado.')
        changes = {**request.data, 'fecha_respuesta': timezone.now().isoformat()}
        payload = {key: value for key, value in document.items() if key != '_id'}
        payload.update(changes)
        validate_document('incidencias_entregas', payload)
        if not collection.update_one(scope, {'$set': changes}).matched_count:
            raise NotFound()
        document.update(changes)
        return Response(read_document('incidencias_entregas', document))


class CustomerOptionsView(DocumentView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        owner = company(request)
        orders = Pedido.objects.filter(restauranteid=owner.pk).order_by('-fechapedido')
        names=company_names(orders.values_list('proveedorid',flat=True))
        return Response({'pedidos': [{'id': p.pk, 'proveedor': names.get(p.proveedorid,'Proveedor')} for p in orders],
                         'categorias': list(Categoria.objects.values('id', 'nombrecategoria'))})
