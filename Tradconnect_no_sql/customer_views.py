"""Operaciones de clientes y proveedores con alcance derivado del JWT."""
from uuid import uuid4
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from config.mongodb import get_database
from TradConnect.sql_models import SqlPedido as Pedido, SqlCategoria as Categoria
from TradConnect.identities import company as mongo_company, company_names, users
from .views import DocumentView
from .services import validate_document, read_document


def read_comment_interactions(comments, interaction_docs):
    comment_by_id = {comment['_id']: comment for comment in comments}
    user_ids = list({
        item.get('usuario_id')
        for item in interaction_docs
        if item.get('usuario_id')
    })
    company_ids = list({
        company_id
        for comment in comments
        for company_id in (comment.get('cliente_empresa_id'), comment.get('proveedor_empresa_id'))
        if company_id
    })
    users_by_company = {}
    if user_ids and company_ids:
        for user in users().find(
            {'usuario_id': {'$in': user_ids}, 'empresa_id': {'$in': company_ids}},
            {'usuario_id': 1, 'nombre_usuario': 1, 'empresa_id': 1},
        ):
            if user.get('usuario_id') and user.get('empresa_id'):
                users_by_company[(user['usuario_id'], user['empresa_id'])] = user

    interactions_by_comment = {}
    for interaction in interaction_docs:
        comment = comment_by_id.get(interaction.get('comentario_id'))
        author = next((
            users_by_company.get((interaction.get('usuario_id'), company_id))
            for company_id in (
                (comment or {}).get('cliente_empresa_id'),
                (comment or {}).get('proveedor_empresa_id'),
            )
            if (interaction.get('usuario_id'), company_id) in users_by_company
        ), None)
        if comment is None or author is None:
            continue
        item = read_document('interacciones_comentario', interaction)
        author_name = author.get('nombre_usuario')
        author_name = author_name.strip() if isinstance(author_name, str) else ''
        company_name = (
            comment.get('proveedor_nombre')
            if author.get('empresa_id') == comment.get('proveedor_empresa_id')
            else comment.get('cliente_nombre')
        )
        item['usuario_nombre'] = author_name or company_name or 'Usuario'
        interactions_by_comment.setdefault(interaction['comentario_id'], []).append(item)
    return interactions_by_comment

COLLECTIONS = {'incidencias_entregas', 'evaluaciones_proveedores',
               'comentarios_post_compra', 'preferencias_negocio', 'necesidades_no_satisfechas'}
COMPANY_READ_COLLECTIONS = {
    'preferencias_negocio', 'preferencias_categorias', 'preferencias_productos',
    'preferencias_metodos_pago', 'evaluaciones_proveedores',
    'transacciones_no_exitosas', 'sustituciones_ofrecidas',
    'incidencias_entregas', 'evidencias_incidencia',
    'comentarios_post_compra', 'necesidades_no_satisfechas',
}
PROVIDER_READ_COLLECTIONS = {
    'evaluaciones_proveedores', 'transacciones_no_exitosas',
    'sustituciones_ofrecidas', 'incidencias_entregas',
    'evidencias_incidencia', 'comentarios_post_compra',
}
PREFERENCE_CHILDREN = {
    'preferencias_categorias', 'preferencias_productos',
    'preferencias_metodos_pago',
}


def company_collection_query(database, collection, owner_id, provider):
    if collection not in COMPANY_READ_COLLECTIONS:
        raise NotFound()
    if provider and collection not in PROVIDER_READ_COLLECTIONS:
        raise PermissionDenied()

    if collection == 'preferencias_negocio':
        return {'empresa_id': owner_id}
    if collection in PREFERENCE_CHILDREN:
        preferences = database['preferencias_negocio'].find(
            {'empresa_id': owner_id},
            {'_id': 1},
        )
        return {'preferencia_id': {'$in': [item['_id'] for item in preferences]}}
    if collection == 'evidencias_incidencia':
        field = 'proveedor_empresa_id' if provider else 'cliente_empresa_id'
        incidents = database['incidencias_entregas'].find(
            {field: owner_id},
            {'_id': 1},
        )
        return {'incidencia_id': {'$in': [item['_id'] for item in incidents]}}
    if collection == 'sustituciones_ofrecidas':
        field = 'proveedor_empresa_id' if provider else 'cliente_empresa_id'
        transactions = database['transacciones_no_exitosas'].find(
            {field: owner_id},
            {'_id': 1},
        )
        return {'transaccion_id': {'$in': [item['_id'] for item in transactions]}}

    field = 'proveedor_empresa_id' if provider else 'cliente_empresa_id'
    return {field: owner_id}


def company(request, provider=False):
    return mongo_company(request, provider)


class CustomerDocumentsView(DocumentView):
    permission_classes = [IsAuthenticated]

    def get(self, request, collection):
        if collection not in COMPANY_READ_COLLECTIONS:
            raise NotFound()
        provider = request.user.rolid.nombrerol.casefold() == 'proveedor'
        owner = company(request, provider)
        try:
            offset = int(request.query_params.get('offset', 0))
        except ValueError:
            raise ValidationError('offset inv?lido.')
        if offset < 0:
            raise ValidationError('offset inv?lido.')
        db = get_database()
        query = company_collection_query(db, collection, str(owner.pk), provider)
        sort_field = (
            'fecha_actualizacion' if collection == 'preferencias_negocio'
            else 'fecha' if collection in {
                'evaluaciones_proveedores', 'transacciones_no_exitosas',
                'incidencias_entregas', 'comentarios_post_compra',
                'necesidades_no_satisfechas',
            }
            else '_id'
        )
        sort = [(sort_field, -1)]
        if sort_field != '_id':
            sort.append(('_id', -1))
        docs = list(db[collection].find(query).sort(sort).skip(offset).limit(50))
        results = [read_document(collection, doc) for doc in docs]
        if collection == 'comentarios_post_compra' and docs:
            comment_ids = [doc['_id'] for doc in docs]
            interactions = db['interacciones_comentario'].find(
                {'comentario_id': {'$in': comment_ids}}
            ).sort([('fecha', 1), ('_id', 1)])
            interactions_by_comment = read_comment_interactions(docs, list(interactions))
            for item, doc in zip(results, docs):
                item['interacciones'] = interactions_by_comment.get(doc['_id'], [])
        return Response({'results': results, 'offset': offset})

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
            if collection == 'comentarios_post_compra':
                user_name = request.user.document.get('nombre_usuario')
                user_email = request.user.document.get('correo')
                payload['usuario_id'] = str(request.user.pk)
                payload['usuario_nombre'] = (user_name.strip() if isinstance(user_name, str) else '') or (
                    user_email.strip() if isinstance(user_email, str) else ''
                )
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


class CommentInteractionsView(DocumentView):
    permission_classes = [IsAuthenticated]

    def get_comment(self, request, pk):
        role = request.user.rolid.nombrerol.casefold()
        if role not in {'cliente', 'restaurante', 'proveedor'}:
            raise PermissionDenied('Solo las empresas participantes pueden consultar este comentario.')
        owner = company(request, provider=role == 'proveedor')
        scope_field = 'proveedor_empresa_id' if role == 'proveedor' else 'cliente_empresa_id'
        comment = get_database()['comentarios_post_compra'].find_one({
            '_id': pk,
            scope_field: str(owner.pk),
        })
        if comment is None:
            raise NotFound('Comentario no encontrado para tu empresa.')
        return comment

    def get(self, request, pk):
        self.get_comment(request, pk)
        try:
            offset = int(request.query_params.get('offset', 0))
        except (ValueError, TypeError):
            raise ValidationError('offset debe ser un entero.')
        if offset < 0:
            raise ValidationError('offset debe ser >= 0.')
        interaction_docs = list(get_database()['interacciones_comentario'].find(
            {'comentario_id': pk}
        ).sort([('fecha', 1), ('_id', 1)]).skip(offset).limit(50))
        interactions_by_comment = read_comment_interactions([comment], interaction_docs)
        return Response({
            'results': interactions_by_comment.get(pk, []),
            'offset': offset,
        })

    def post(self, request, pk):
        comment = self.get_comment(request, pk)
        if not isinstance(request.data, dict) or set(request.data) != {'mensaje'}:
            raise ValidationError('Envía únicamente el mensaje de respuesta.')
        message = request.data['mensaje']
        if not isinstance(message, str) or not message.strip() or len(message.strip()) > 2000:
            raise ValidationError('La respuesta debe tener entre 1 y 2000 caracteres.')
        user_name = request.user.document.get('nombre_usuario')
        user_email = request.user.document.get('correo')
        payload = {
            'comentario_id': pk,
            'fecha': timezone.now(),
            'tipo': 'Respuesta',
            'mensaje': message.strip(),
            'usuario_id': str(request.user.pk),
            'usuario_nombre': (user_name.strip() if isinstance(user_name, str) else '') or (
                user_email.strip() if isinstance(user_email, str) else ''
            ),
        }
        document = validate_document('interacciones_comentario', payload)
        document['_id'] = 'int_' + uuid4().hex
        get_database()['interacciones_comentario'].insert_one(document)
        response = read_document('interacciones_comentario', document)
        response['usuario_nombre'] = payload['usuario_nombre']
        return Response(response, status=201)


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
