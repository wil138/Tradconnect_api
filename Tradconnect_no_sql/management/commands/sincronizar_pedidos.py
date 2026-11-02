from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError
from pymongo.errors import PyMongoError

from config.mongodb import get_database
from TradConnect.models import Pedido
from Tradconnect_no_sql.order_sync import SOURCES, sync_order, web_document
from Tradconnect_no_sql.projections import DocumentModel


class Command(BaseCommand):
    help = 'Recarga/verifica pedidos, detalles, historial y la proyección web desde SQL.'

    def add_arguments(self, parser):
        parser.add_argument('--pedido', type=int, action='append')
        parser.add_argument('--verificar', action='store_true', help='Compara documentos sin escribir.')
        parser.add_argument('--limpiar', action='store_true', help='Elimina proyecciones de pedidos ausentes en SQL.')

    def differences(self, order_id, database):
        differences = []
        order = Pedido.objects.filter(pk=order_id).first()
        for model in SOURCES:
            name = model._meta.model_name
            queryset = model.objects.filter(pk=order_id) if model is Pedido else model.objects.filter(pedidoid_id=order_id)
            expected = {instance.pk: DocumentModel(model).serialize(instance) for instance in queryset}
            query = {'_id': order_id} if model is Pedido else {'pedidoid': order_id}
            actual = {doc['_id']: doc for doc in database[name].find(query)}
            if expected != actual:
                differences.append(name)
        actual_web = database['pedidos_web'].find_one({'_id': order_id})
        if actual_web:
            actual_web.pop('sincronizado_en', None)
        if (web_document(order) if order else None) != actual_web:
            differences.append('pedidos_web')
        return differences

    def handle(self, *args, **options):
        try:
            database = get_database()
            ids = set(options['pedido'] or Pedido.objects.values_list('pk', flat=True))
            if not options['pedido'] and (options['limpiar'] or options['verificar']):
                for name in ('pedido', 'pedidos_web'):
                    ids.update(doc['_id'] for doc in database[name].find({}, {'_id': 1}))
                # Incluye huérfanos aunque falte el documento padre.
                for name in ('detallepedido', 'historialestadopedido'):
                    ids.update(database[name].distinct('pedidoid'))
            failures = 0
            for order_id in sorted(ids):
                if options['verificar']:
                    different = self.differences(order_id, database)
                    if different:
                        failures += 1
                        self.stderr.write(f'Pedido {order_id}: diferencias en {", ".join(different)}')
                else:
                    sync_order(order_id, database)
            for model in SOURCES:
                name = model._meta.model_name
                if not options['pedido']:
                    self.stdout.write(f'{name}: SQL={model.objects.count()}, Mongo={database[name].count_documents({})}')
            if failures:
                raise CommandError(f'{failures} pedidos con diferencias. Ejecuta la recarga para corregirlos.')
            self.stdout.write(self.style.SUCCESS(f'{len(ids)} pedidos ' + ('verificados.' if options['verificar'] else 'sincronizados.')))
        except (ImproperlyConfigured, DatabaseError, PyMongoError) as exc:
            raise CommandError('Proceso incompleto: revisa SQL y MongoDB. La recarga se puede repetir.') from exc
