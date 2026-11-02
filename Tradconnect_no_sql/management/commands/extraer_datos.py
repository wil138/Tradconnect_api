"""Extrae los modelos reales SQL; nunca genera registros ficticios."""
import json
import re
from collections import Counter
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import connection, transaction, DatabaseError
from Tradconnect_no_sql.cleaning import clean_value, prepare_password


class Command(BaseCommand):
    help = 'Audita y exporta datos SQL limpios a JSONL; opcionalmente actualiza hashes SQL.'

    def add_arguments(self, parser):
        parser.add_argument('--fuente', choices=('sql', 'mongo', 'ambas'), default='sql')
        parser.add_argument('--directorio', default='exportaciones')
        parser.add_argument('--restablecer-passwords', action='store_true')
        parser.add_argument('--password-env')
        parser.add_argument('--salida', help='Archivo JSONL nuevo. No sobrescribe archivos existentes.')
        parser.add_argument('--aplicar-hashes', action='store_true', help='Actualiza solo contrasenas SQL sin hash reconocido.')
        parser.add_argument('--batch-size', type=int, default=500)

    def handle(self, *args, **options):
        if options.get('fuente', 'sql') != 'sql' or options.get('restablecer_passwords'):
            if options.get('salida') or options.get('aplicar_hashes'):
                raise CommandError('Usa --directorio para separar fuentes; --salida y --aplicar-hashes son solo SQL.')
            from django.core.management import call_command
            return call_command('extraer_bases', fuente=options['fuente'], directorio=options['directorio'],
                restablecer_passwords=options['restablecer_passwords'], password_env=options['password_env'], stdout=self.stdout, stderr=self.stderr)
        if options['batch_size'] < 1:
            raise CommandError('--batch-size debe ser positivo.')
        counts, passwords = Counter(), Counter()
        pending = []
        output = None
        created = False
        path = Path(options['salida']).resolve() if options['salida'] else None
        stage = 'abrir archivo de salida'
        try:
            if path:
                output = path.open('x', encoding='utf-8')
                created = True
            stage = 'consultar tablas reales SQL'
            with connection.cursor() as cursor:
                cursor.execute("SELECT TABLE_SCHEMA, TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE' AND TABLE_NAME <> 'sysdiagrams' ORDER BY TABLE_SCHEMA, TABLE_NAME")
                tables = cursor.fetchall()
            user_tables = 0
            for schema, table in tables:
                stage = f'leer tabla {schema}.{table}'
                quoted = connection.ops.quote_name
                qualified = quoted(schema) + '.' + quoted(table)
                with connection.cursor() as cursor:
                    cursor.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND CONSTRAINT_NAME IN (SELECT CONSTRAINT_NAME FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND CONSTRAINT_TYPE = 'PRIMARY KEY') ORDER BY ORDINAL_POSITION", [schema, table, schema, table])
                    primary_keys = [row[0] for row in cursor.fetchall()]
                    cursor.execute('SELECT * FROM ' + qualified)
                    columns = [col[0] for col in cursor.description]
                    # Nombres de columnas reales; nunca asumir columnas del ORM.
                    secret_columns = {col for col in columns if col.casefold().replace('_', '') in
                        ('contrasena', 'password', 'passwordhash', 'clave', 'accesstoken', 'refreshtoken', 'secret', 'apikey')}
                    password_column = next((col for col in secret_columns if col.casefold().replace('_', '') in ('contrasena', 'password', 'passwordhash', 'clave')), None)
                    is_user = table.casefold() in ('usuario', 'usuarios', 'user', 'users', 'auth_user')
                    if is_user:
                        user_tables += 1
                    while True:
                        rows = cursor.fetchmany(options['batch_size'])
                        if not rows:
                            break
                        for row in rows:
                            raw = dict(zip(columns, row))
                            document = {col: clean_value(value) for col, value in raw.items() if col not in secret_columns}
                            if is_user and password_column:
                                prepared, state = prepare_password(raw[password_column])
                                passwords[state] += 1
                                if state == 'revisar':
                                    document['requiere_revision_password'] = True
                                elif state in ('hasheado', 'sin_clave') and options['aplicar_hashes']:
                                    if not primary_keys:
                                        raise CommandError(f'{schema}.{table}: falta clave primaria para actualizar hashes.')
                                    pending.append((qualified, primary_keys, {key: raw[key] for key in primary_keys}, password_column, raw[password_column], prepared))
                            if output:
                                output.write(json.dumps({'coleccion': table.lower(), 'esquema': schema, 'documento': document}, cls=DjangoJSONEncoder, ensure_ascii=False) + '\n')
                            counts[schema + '.' + table] += 1
            if not user_tables:
                self.stderr.write('Aviso: esta base SQL no contiene tablas de usuarios reconocidas. No se modificaran contrasenas; verifica si los usuarios estan en MongoDB u otra base.')
            stage = 'actualizar hashes'
            if options['aplicar_hashes']:
                if passwords['revisar']:
                    raise CommandError('Hay contrasenas de formato ambiguo; revisa su origen antes de aplicar hashes.')
                # La actualizacion condicional detecta cambios concurrentes; todo revierte si falla una.
                with transaction.atomic():
                    with connection.cursor() as cursor:
                        for qualified, keys, values, column, previous, prepared in pending:
                            conditions = [connection.ops.quote_name(key) + ' = %s' for key in keys]
                            params = [prepared] + [values[key] for key in keys]
                            secret = connection.ops.quote_name(column)
                            if previous is None:
                                conditions.append(secret + ' IS NULL')
                            else:
                                # Comparacion binaria: SQL Server puede ignorar espacios finales y mayusculas.
                                conditions.append('CONVERT(varbinary(max), ' + secret + ') = CONVERT(varbinary(max), %s)')
                                params.append(previous)
                            cursor.execute('UPDATE ' + qualified + ' SET ' + secret + ' = %s WHERE ' + ' AND '.join(conditions), params)
                            if cursor.rowcount != 1:
                                raise CommandError('Un usuario cambio durante la extraccion; repite el comando.')
            if output:
                output.close()
            self.stdout.write(json.dumps({'registros': dict(counts), 'passwords': dict(passwords),
                'hashes_aplicados': len(pending) if options['aplicar_hashes'] else 0,
                'exportado': bool(path)}, ensure_ascii=False))
        except Exception as exc:
            if output:
                output.close()
            if created:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass
            if isinstance(exc, CommandError):
                raise
            # Nunca mostrar parametros SQL, registros ni credenciales.
            detail = f'Fallo al {stage}. Tipo: {type(exc).__name__}.'
            if isinstance(exc, FileExistsError):
                detail += ' El archivo ya existe; usa otro nombre de salida.'
            elif isinstance(exc, PermissionError):
                detail += ' No hay permiso para escribir el archivo.'
            elif isinstance(exc, DatabaseError):
                codes = sorted(set(re.findall(r"\b(?:[0-9]{2}[A-Z0-9]{3}|HY[A-Z0-9]{3}|IM[A-Z0-9]{3})\b", str(exc))))
                detail += ' SQLSTATE: ' + (', '.join(codes) or 'no disponible') + '.'
                if any(c.startswith('08') or c in ('HYT00', 'HYT01') for c in codes):
                    detail += ' Revisa servidor, instancia, puerto y disponibilidad de SQL Server.'
                elif '28000' in codes:
                    detail += ' Revisa autenticacion y permisos SQL/Windows.'
                elif '42S02' in codes:
                    detail += ' Falta una tabla o su nombre/esquema no coincide con Django.'
                elif '42S22' in codes:
                    detail += ' Una columna del modelo Django no existe en SQL.'
            raise CommandError(detail) from None
