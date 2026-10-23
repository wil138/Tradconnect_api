import getpass
import json
import os
from io import StringIO
from pathlib import Path
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from config.mongodb import get_database
from Tradconnect_no_sql.data_pipeline import reset_passwords, export_mongo


class Command(BaseCommand):
    help = 'Separa datos SQL y NoSQL; permite restablecer password_hash explicitamente.'

    def add_arguments(self, parser):
        parser.add_argument('--fuente', choices=('sql', 'mongo', 'ambas'), default='ambas')
        parser.add_argument('--directorio', default='exportaciones')
        parser.add_argument('--restablecer-passwords', action='store_true')
        parser.add_argument('--password-env', help='Variable de entorno con la clave; si se omite, se solicita oculta.')

    def handle(self, *args, **options):
        root = Path(options['directorio']).resolve()
        sql_target, mongo_target = root / 'sql' / 'datos_limpios.jsonl', root / 'nosql' / 'datos_limpios.jsonl'
        use_sql = options['fuente'] in ('sql', 'ambas')
        use_mongo = options['fuente'] in ('mongo', 'ambas')
        if options['restablecer_passwords'] and not use_mongo:
            raise CommandError('El restablecimiento de password_hash requiere --fuente mongo o ambas.')
        for target, enabled in ((sql_target, use_sql), (mongo_target, use_mongo)):
            if enabled and target.exists():
                raise CommandError('Ya existe un archivo de salida; usa otro --directorio para conservar la exportacion previa.')
        database = None
        password = None
        report = {}
        try:
            if use_mongo:
                database = get_database()
                database.command('ping')
            if options['restablecer_passwords']:
                password = os.environ.get(options['password_env']) if options['password_env'] else getpass.getpass('Nueva clave para todos los usuarios: ')
                if not password:
                    raise CommandError('La clave esta vacia o no existe la variable indicada.')
                if 'usuarios_empresas_roles' not in database.list_collection_names():
                    raise CommandError('No existe usuarios_empresas_roles en la base seleccionada.')
            # Exportar SQL primero; no restablecer claves si falla la extraccion SQL.
            if use_sql:
                sql_target.parent.mkdir(parents=True, exist_ok=True)
                capture = StringIO()
                call_command('extraer_datos', salida=str(sql_target), stdout=capture, stderr=self.stderr)
                report['sql'] = json.loads(capture.getvalue())
            if options['restablecer_passwords']:
                report['password_hash'] = {}
                reset_passwords(database, password, report['password_hash'], progress=self.stdout.write)
                self.stdout.write('Restablecimiento MongoDB completado y verificado.')
            if use_mongo:
                mongo_target.parent.mkdir(parents=True, exist_ok=True)
                report['nosql'] = export_mongo(database, mongo_target)
            self.stdout.write(json.dumps(report, ensure_ascii=False))
        except CommandError:
            raise
        except Exception as exc:
            raise CommandError(f'Proceso incompleto ({type(exc).__name__}). Conserva el informe previo; revisa configuracion y permisos. No se garantiza rollback entre SQL, MongoDB y archivos.') from None
