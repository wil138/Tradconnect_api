import json
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from config.mongodb import get_database
from Tradconnect_no_sql.restore_data import load_sources, sql_metadata, replace_data


class Command(BaseCommand):
    help = 'Valida o sustituye SQL y MongoDB desde los archivos separados, con respaldo.'

    def add_arguments(self, parser):
        parser.add_argument('--directorio', default='exportaciones_separadas')
        parser.add_argument('--respaldo', default='respaldos/antes_importacion')
        parser.add_argument('--aplicar', action='store_true')

    def handle(self, *args, **options):
        try:
            root = Path(options['directorio']).resolve()
            sql, mongo = load_sources(root)
            sql_metadata(sql)
            db = get_database(); db.command('ping')
            report = {'sql_registros':sum(map(len,sql.values())), 'nosql_documentos':sum(map(len,mongo.values()))}
            if options['aplicar']:
                report = replace_data(sql, mongo, db, Path(options['respaldo']).resolve(), self.stdout.write)
            report['aplicado'] = options['aplicar']
            self.stdout.write(json.dumps(report))
        except CommandError:
            raise
        except Exception as exc:
            raise CommandError(f'Importacion incompleta ({type(exc).__name__}). Revisa el respaldo y el ultimo avance. No se muestran datos privados.') from None
