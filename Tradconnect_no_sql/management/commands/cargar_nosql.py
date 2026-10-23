from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError
from pymongo import ReplaceOne
from pymongo.errors import PyMongoError
from Tradconnect_no_sql.projections import get_document_models


class Command(BaseCommand):
    help = 'Copia SQL a MongoDB por ID sin modificar SQL ni replicar usuarios.'

    def add_arguments(self, parser):
        parser.add_argument('--coleccion', action='append', dest='collections')
        parser.add_argument('--batch-size', type=int, default=500)

    def handle(self, *args, **options):
        models = get_document_models()
        names = options['collections'] or list(models)
        unknown = set(names) - models.keys()
        if unknown:
            raise CommandError('Colecciones desconocidas: ' + ', '.join(sorted(unknown)))
        size = options['batch_size']
        if size < 1:
            raise CommandError('--batch-size debe ser positivo.')
        try:
            for name in names:
                model = models[name]
                collection = model.collection
                batch, count = [], 0
                for instance in model.sql_model.objects.using('default').order_by('pk').iterator(chunk_size=size):
                    batch.append(ReplaceOne({'_id': instance.pk}, model.serialize(instance), upsert=True))
                    count += 1
                    if len(batch) >= size:
                        collection.bulk_write(batch, ordered=False)
                        batch = []
                if batch:
                    collection.bulk_write(batch, ordered=False)
                self.stdout.write(self.style.SUCCESS(f'{name}: {count} documentos cargados'))
        except (PyMongoError, ImproperlyConfigured, DatabaseError) as exc:
            raise CommandError('Carga incompleta. Revisa SQL Server y MongoDB; '
                               'puedes repetir el comando para completarla.') from exc
