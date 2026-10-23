"""Proyección repetible de pedidos SQL, sincronizada después del commit."""
import json
import logging

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.renderers import JSONRenderer

from config.mongodb import get_database
from TradConnect.models import Pedido, Detallepedido, Historialestadopedido
from TradConnect.serializers import PedidoSerializer, HistorialEstadoPedidoSerializer
from .projections import DocumentModel

logger = logging.getLogger(__name__)
SOURCES = (Pedido, Detallepedido, Historialestadopedido)


def web_document(order):
    # Usa el contrato de la web y agrega el historial completo.
    payload = dict(PedidoSerializer(order).data)
    history = order.historialestadopedido_set.select_related('estadoid').order_by('fechacambio', 'pk')
    payload['historial'] = HistorialEstadoPedidoSerializer(history, many=True).data
    return {'_id': order.pk, **json.loads(JSONRenderer().render(payload))}


def sync_order(order_id, database=None):
    database = database if database is not None else get_database()
    order = Pedido.objects.filter(pk=order_id).first()
    if order is None:
        database['pedidos_web'].delete_one({'_id': order_id})
        database['pedido'].delete_one({'_id': order_id})
        for name in ('detallepedido', 'historialestadopedido'):
            database[name].delete_many({'pedidoid': order_id})
        return
    # Publica el documento web completo al final: no se leen colecciones parciales.
    document = web_document(order)
    database['pedido'].replace_one({'_id': order_id}, DocumentModel(Pedido).serialize(order), upsert=True)
    for model in SOURCES[1:]:
        collection = database[model._meta.model_name]
        ids = []
        for instance in model.objects.filter(pedidoid_id=order_id).order_by('pk').iterator():
            collection.replace_one({'_id': instance.pk}, DocumentModel(model).serialize(instance), upsert=True)
            ids.append(instance.pk)
        collection.delete_many({'pedidoid': order_id, '_id': {'$nin': ids}})
    document['sincronizado_en'] = timezone.now().isoformat()
    database['pedidos_web'].replace_one({'_id': order_id}, document, upsert=True)


def schedule_order_sync(order_id, using='default'):
    if using != 'default' or not settings.MONGODB_URI:
        return

    def after_commit():
        try:
            sync_order(order_id)
        except Exception:
            # SQL ya se confirmó: un fallo de proyección no debe convertirlo en un 500.
            # No registrar URI ni datos del pedido; permitir recuperación por comando.
            logger.error('No se sincronizó el pedido SQL %s. Ejecuta sincronizar_pedidos --pedido %s.',
                         order_id, order_id)

    transaction.on_commit(after_commit, using=using)
