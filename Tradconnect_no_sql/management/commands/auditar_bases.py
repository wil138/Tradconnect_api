import json

from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError
from pymongo.errors import PyMongoError

from config.mongodb import get_database
from Tradconnect_no_sql.audit import audit_databases, has_differences


class Command(BaseCommand):
    help = 'Compara conteos, claves y vínculos SQL/Mongo sin escribir ni consultar hashes.'

    def add_arguments(self, parser):
        parser.add_argument('--limite-ids', type=int, default=20,
                            help='Máximo de IDs por diferencia; 0 muestra solo cantidades.')

    def handle(self, *args, **options):
        if options['limite_ids'] < 0:
            raise CommandError('--limite-ids debe ser >= 0.')
        try:
            report = audit_databases(get_database(), options['limite_ids'])
        except (ImproperlyConfigured, DatabaseError, PyMongoError):
            raise CommandError('Auditoría incompleta. Revisa la configuración y conectividad de SQL/Mongo; no se escribieron datos.') from None
        self.stdout.write(json.dumps(report, ensure_ascii=False, indent=2, default=str))
        if has_differences(report):
            raise CommandError('Se encontraron diferencias de claves o vínculos. No se modificaron las bases.')
        self.stdout.write(self.style.SUCCESS('Claves y vínculos coinciden. No se compararon importes, fechas ni otros contenidos.'))
