from uuid import uuid4

from django.contrib.auth.hashers import identify_hasher
from pydantic import ValidationError as SchemaError
from rest_framework.exceptions import NotFound, ValidationError

from config.mongodb import get_database
from TradConnect import sql_models as sql
from .models import SCHEMAS


SQL_REFERENCES = {
    'sucursal_id_sql': sql.SqlSucursal,
    'cliente_sucursal_id_sql': sql.SqlSucursal,
    'proveedor_sucursal_id_sql': sql.SqlSucursal,
    'categoria_id_sql': sql.SqlCategoria,
    'producto_id_sql': sql.SqlProducto,
    'metodo_pago_id_sql': sql.SqlMetodopago,
    'pedido_id_sql': sql.SqlPedido,
}
MONGO_REFERENCES = {
    'preferencia_id': 'preferencias_negocio',
    'transaccion_id': 'transacciones_no_exitosas',
    'incidencia_id': 'incidencias_entregas',
    'comentario_id': 'comentarios_post_compra',
}


def schemas(name):
    if name not in SCHEMAS:
        raise NotFound('Colección desconocida.')
    return SCHEMAS[name]


def validate_document(name, payload, database=None, staged=None):
    create_schema, _ = schemas(name)
    try:
        instance = create_schema.model_validate(payload)
    except SchemaError as exc:
        # No incluir input ni context: podrían contener contraseñas.
        raise ValidationError([{'campo': '.'.join(map(str, e['loc'])), 'mensaje': e['msg']}
                              for e in exc.errors(include_input=False, include_context=False)])
    document = instance.model_dump(mode='json')
    for field, model in SQL_REFERENCES.items():
        value = document.get(field)
        if value is not None and not model.objects.filter(pk=value).exists():
            raise ValidationError({field: 'La referencia SQL no existe.'})
    for field, collection in MONGO_REFERENCES.items():
        value = document.get(field)
        if value is not None:
            database = database if database is not None else get_database()
            exists = staged is not None and (collection, value) in staged
            if not exists and database[collection].find_one({'_id': value}, {'_id': 1}) is None:
                raise ValidationError({field: 'El documento relacionado no existe.'})
    if name == 'usuarios_empresas_roles':
        try:
            identify_hasher(document['password_hash'])
        except ValueError:
            raise ValidationError({'password_hash': 'Se requiere un hash Django reconocido, no una contraseña en texto.'})
    return document


def read_document(name, document):
    return schemas(name)[1].model_validate(document).model_dump(mode='json', by_alias=True)


def create_document(name, payload):
    schemas(name)
    database = get_database()
    document = validate_document(name, payload, database)
    prefix = 'uer' if name == 'usuarios_empresas_roles' else name
    document['_id'] = f'{prefix}_{uuid4().hex}'
    database[name].insert_one(document)
    return read_document(name, document)
