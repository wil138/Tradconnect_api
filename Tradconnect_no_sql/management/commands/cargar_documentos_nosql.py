import json
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError
from pymongo import ReplaceOne
from pymongo.errors import PyMongoError
from rest_framework.exceptions import APIException

from config.mongodb import get_database
from Tradconnect_no_sql.services import schemas, validate_document


class Command(BaseCommand):
    help = 'Importa JSON {coleccion: [{_id: ..., campos...}]} validando antes de escribir.'

    def add_arguments(self, parser):
        parser.add_argument('archivo', type=Path)
        parser.add_argument('--validar', action='store_true', help='Valida sin escribir en MongoDB.')

    def handle(self, *args, **options):
        try:
            data = json.loads(options['archivo'].read_text(encoding='utf-8-sig'))
            if not isinstance(data, dict) or not data:
                raise CommandError('Se requiere un objeto con colecciones y listas de documentos.')
            staged, prepared = set(), {}
            for name, documents in data.items():
                schemas(name)
                if not isinstance(documents, list):
                    raise CommandError(f'{name}: se requiere una lista.')
                for document in documents:
                    if not isinstance(document, dict) or not isinstance(document.get('_id'), str) or not document['_id']:
                        raise CommandError(f'{name}: cada documento requiere _id de texto no vacío.')
                    key = (name, document['_id'])
                    if key in staged:
                        raise CommandError(f'{name}: ID duplicado dentro del archivo.')
                    staged.add(key)
            database = get_database()
            for name, documents in data.items():
                prepared[name] = []
                for document in documents:
                    payload = {key: value for key, value in document.items() if key != '_id'}
                    valid = validate_document(name, payload, database, staged)
                    valid['_id'] = document['_id']
                    prepared[name].append(valid)
            if options['validar']:
                self.stdout.write(self.style.SUCCESS('Archivo válido; no se escribieron datos.'))
                return
            for name, documents in prepared.items():
                for start in range(0, len(documents), 500):
                    database[name].bulk_write([
                        ReplaceOne({'_id': doc['_id']}, doc, upsert=True)
                        for doc in documents[start:start + 500]], ordered=False)
                self.stdout.write(self.style.SUCCESS(f'{name}: {len(documents)} documentos cargados.'))
        except (OSError, ValueError, APIException, ImproperlyConfigured, DatabaseError, PyMongoError) as exc:
            # No imprimir payloads ni credenciales de conexión.
            if isinstance(exc, APIException):
                raise CommandError(str(exc.detail)) from exc
            raise CommandError('No se completó la importación. Revisa archivo, configuración y conexiones; '
                               'si hubo escrituras parciales, repite el mismo archivo.') from exc
