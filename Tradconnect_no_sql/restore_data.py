"""Reemplazo de datos exportados conservando esquema, claves e indices."""
import json
import re
import hashlib
from collections import defaultdict
from uuid import uuid4
from datetime import datetime, date, timezone
from decimal import Decimal
from bson import json_util
from django.core.management.base import CommandError
from django.db import connection, transaction
from .cleaning import clean_value
from .projections import document_value


def load_sources(root):
    sql, mongo = defaultdict(list), defaultdict(list)
    for source, target, loader in (('sql', sql, json.loads), ('nosql', mongo, json_util.loads)):
        with (root / source / 'datos_limpios.jsonl').open(encoding='utf-8') as stream:
            for number, line in enumerate(stream, 1):
                row = loader(line)
                document = row.get('documento')
                name = row.get('coleccion')
                if not isinstance(document, dict) or not isinstance(name, str) or not name or name.startswith(('system.', '__tc_')):
                    raise CommandError(f'Registro invalido en {source}, linea {number}.')
                key = (row.get('esquema', 'dbo'), name) if source == 'sql' else name
                target[key].append(document)
    if not sql or not mongo:
        raise CommandError('Ambas fuentes deben contener registros; no se permite vaciar una base por archivo vacio.')
    for name, documents in mongo.items():
        ids = [json_util.dumps(doc.get('_id'), sort_keys=True) for doc in documents]
        if any('_id' not in doc for doc in documents) or len(ids) != len(set(ids)):
            raise CommandError(f'IDs faltantes o duplicados en {name}.')
    return dict(sql), dict(mongo)


def sort_tables(keys, edges):
    pending = set(keys); result = []
    while pending:
        ready = sorted(key for key in pending if not any(child == key and parent in pending for child, parent in edges))
        if not ready:
            raise CommandError('Las relaciones SQL contienen un ciclo; no se deshabilitaran las restricciones.')
        result.extend(ready); pending.difference_update(ready)
    return result


def fingerprint(documents):
    # Independiente del orden de consulta, conservando tipos BSON.
    hashes = sorted(hashlib.sha256(json_util.dumps(doc, sort_keys=True, json_options=json_util.CANONICAL_JSON_OPTIONS).encode()).hexdigest() for doc in documents)
    return hashlib.sha256(''.join(hashes).encode()).hexdigest()


def sql_metadata(sql):
    quote = connection.ops.quote_name
    qualified = lambda key: quote(key[0]) + '.' + quote(key[1])
    with connection.cursor() as cursor:
        cursor.execute("SELECT TABLE_SCHEMA,TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE' AND TABLE_NAME <> 'sysdiagrams'")
        real = {(s.casefold(), t.casefold()): (s, t) for s,t in cursor.fetchall()}
        selected = {}
        for key, documents in sql.items():
            actual = real.get((key[0].casefold(), key[1].casefold()))
            if actual is None:
                raise CommandError('Una tabla del archivo no existe en la base seleccionada.')
            selected[actual] = documents
        # Exigir toda la base evita eliminar padres referenciados por tablas omitidas.
        if set(selected) != set(real.values()):
            raise CommandError('El archivo SQL no contiene todas las tablas de la base. No se modificaron datos.')
        cursor.execute('SELECT OBJECT_SCHEMA_NAME(parent_object_id),OBJECT_NAME(parent_object_id),OBJECT_SCHEMA_NAME(referenced_object_id),OBJECT_NAME(referenced_object_id) FROM sys.foreign_keys')
        edges = [((s,t),(ps,pt)) for s,t,ps,pt in cursor.fetchall()]
        order = sort_tables(selected, edges)
        metadata = {}
        for key in order:
            cursor.execute('SELECT TOP 0 * FROM ' + qualified(key))
            columns = [col[0] for col in cursor.description]
            if any(set(row) != set(columns) for row in selected[key]):
                raise CommandError(f'Las columnas del archivo no coinciden con {key[0]}.{key[1]}.')
            cursor.execute('SELECT c.name FROM sys.columns c WHERE c.object_id = OBJECT_ID(%s) AND c.is_identity = 1', [key[0] + '.' + key[1]])
            identity = bool(cursor.fetchall())
            cursor.execute('SELECT COLUMN_NAME,DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s', list(key))
            types = dict(cursor.fetchall())
            for doc in selected[key]:
                for col in columns:
                    sql_value(doc[col], types[col])
            metadata[key] = (columns, identity, types)
    return selected, order, metadata


def sql_value(value, kind):
    if value is None:
        return None
    if kind in ('decimal', 'numeric', 'money', 'smallmoney'):
        return Decimal(str(value))
    if kind in ('datetime', 'datetime2', 'smalldatetime', 'datetimeoffset') and isinstance(value, str):
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is not None and kind != 'datetimeoffset':
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed
    if kind == 'date' and isinstance(value, str):
        return date.fromisoformat(value)
    return value


def replace_data(sql, mongo, db, backup, progress):
    sql, order, metadata = sql_metadata(sql)
    current = set(db.list_collection_names())
    if set(mongo) != {name for name in current if not name.startswith('system.')}:
        raise CommandError('Las colecciones del archivo no coinciden con la base MongoDB. No se modificaron datos.')
    quote = connection.ops.quote_name
    qualified = lambda key: quote(key[0]) + '.' + quote(key[1])
    backup.mkdir(parents=True, exist_ok=False)
    stages, archives, swapped, snapshots = {}, {}, [], {}
    token = uuid4().hex
    try:
        # Respaldar Mongo en BSON Extended JSON, conservando campos originales.
        with (backup / 'nosql_original.jsonl').open('x', encoding='utf-8') as output:
            for name in sorted(mongo):
                docs = list(db[name].find({}))
                snapshots[name] = fingerprint(docs)
                for doc in docs:
                    output.write(json_util.dumps({'coleccion': name, 'documento': doc}) + '\n')
                stage = '__tc_stage_' + token + '_' + name
                archives[name] = '__tc_backup_' + token + '_' + name
                stages[name] = stage
                options = db[name].options()
                db.create_collection(stage, **options)
                indexes = []
                from pymongo import IndexModel
                for index in db[name].list_indexes():
                    if index['name'] == '_id_':
                        continue
                    spec = dict(index); keys = list(spec.pop('key').items())
                    for field in ('v', 'ns', 'background'):
                        spec.pop(field, None)
                    indexes.append(IndexModel(keys, **spec))
                if indexes:
                    db[stage].create_indexes(indexes)
                for offset in range(0, len(mongo[name]), 500):
                    db[stage].insert_many(mongo[name][offset:offset+500], ordered=True)
                if fingerprint(db[stage].find({})) != fingerprint(mongo[name]):
                    raise CommandError('La verificacion de la coleccion temporal fallo.')
        progress('Respaldo MongoDB y colecciones temporales verificados.')
        with transaction.atomic():
            # Bloquear todas las tablas durante respaldo y sustitucion SQL.
            with connection.cursor() as cursor, (backup / 'sql_original.jsonl').open('x', encoding='utf-8') as output:
                for key in order:
                    cursor.execute('SELECT * FROM ' + qualified(key) + ' WITH (TABLOCKX, HOLDLOCK)')
                    columns = [col[0] for col in cursor.description]
                    while True:
                        rows = cursor.fetchmany(500)
                        if not rows:
                            break
                        for row in rows:
                            output.write(json_util.dumps({'esquema':key[0], 'coleccion':key[1], 'documento':{col:document_value(value) for col,value in zip(columns,row)}}) + '\n')
                progress('Respaldo SQL terminado. Iniciando sustitucion transaccional.')
                for key in reversed(order):
                    cursor.execute('DELETE FROM ' + qualified(key))
                for key in order:
                    columns, identity, types = metadata[key]
                    if identity:
                        cursor.execute('SET IDENTITY_INSERT ' + qualified(key) + ' ON')
                    try:
                        statement = 'INSERT INTO ' + qualified(key) + ' (' + ','.join(quote(col) for col in columns) + ') VALUES (' + ','.join(['%s']*len(columns)) + ')'
                        for offset in range(0, len(sql[key]), 500):
                            values = [tuple(sql_value(doc[col], types[col]) for col in columns) for doc in sql[key][offset:offset+500]]
                            cursor.executemany(statement, values)
                    except Exception as exc:
                        codes = sorted(set(re.findall(r'\b(?:[0-9]{2}[A-Z0-9]{3}|HY[A-Z0-9]{3})\b', str(exc))))
                        raise CommandError(f'Error SQL al insertar {key[0]}.{key[1]}: {type(exc).__name__}; SQLSTATE: ' + ','.join(codes)) from None
                    finally:
                        if identity:
                            cursor.execute('SET IDENTITY_INSERT ' + qualified(key) + ' OFF')
                    cursor.execute('SELECT * FROM ' + qualified(key))
                    rows = [{col:clean_value(value) for col,value in zip(columns,row)} for row in cursor.fetchall()]
                    if fingerprint(rows) != fingerprint(sql[key]):
                        raise CommandError(f'El contenido insertado no coincide con {key[0]}.{key[1]}.')
                    progress(f'{key[1]}: {len(rows)} registros sustituidos y verificados.')
            # Detectar cambios Mongo antes de reemplazar las colecciones activas.
            for name in mongo:
                if fingerprint(db[name].find({})) != snapshots[name]:
                    raise CommandError('MongoDB cambio durante la operacion. SQL se revertira.')
            for name in mongo:
                db[name].rename(archives[name])
                try:
                    db[stages[name]].rename(name)
                except Exception:
                    db[archives[name]].rename(name)
                    raise
                swapped.append(name)
        # SQL confirmado y todas las colecciones activas sustituidas.
    except Exception:
        for name in reversed(swapped):
            db[archives[name]].rename(name, dropTarget=True)
        for stage in stages.values():
            db.drop_collection(stage)
        raise
    for archive in archives.values():
        db.drop_collection(archive)
    return {'sql_registros':sum(map(len,sql.values())), 'sql_tablas':len(sql),
            'nosql_documentos':sum(map(len,mongo.values())), 'nosql_colecciones':len(mongo)}
