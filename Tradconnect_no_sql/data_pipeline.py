"""Extraccion MongoDB y restablecimiento explicito de credenciales."""
import unicodedata
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from bson import json_util
from django.contrib.auth.hashers import make_password, check_password
from django.core.management.base import CommandError

PLAIN_SECRETS = {'password', 'contrasena', 'clave', 'access_token', 'refresh_token', 'api_key', 'secret'}


def clean_document(value, key=None):
    if isinstance(value, dict):
        return {name: clean_document(item, name) for name, item in value.items() if name.lower() not in PLAIN_SECRETS}
    if isinstance(value, list):
        return [clean_document(item, key) for item in value]
    if isinstance(value, str) and key not in ('_id', 'password_hash') and not (key or '').endswith('_id'):
        return unicodedata.normalize('NFC', value).replace('\x00', '').strip()
    return value


def reset_passwords(database, password, report, progress=None):
    collection_name = 'usuarios_empresas_roles'
    if collection_name not in database.list_collection_names():
        raise CommandError('No existe usuarios_empresas_roles en la base MongoDB seleccionada.')
    collection = database[collection_name]
    documents = list(collection.find({}, {'_id': 1, 'usuario_id': 1, 'password_hash': 1}))
    accounts = list(dict.fromkeys(str(doc.get('usuario_id') or doc['_id']) for doc in documents))
    hashes = {}
    # PBKDF2 libera el GIL: calcular con cuatro hilos conserva el algoritmo y sus iteraciones.
    with ThreadPoolExecutor(max_workers=4) as executor:
        for index, (account, hashed) in enumerate(zip(accounts, executor.map(make_password, [password] * len(accounts))), 1):
            hashes[account] = hashed
            if progress and index % 100 == 0:
                progress(f'Hashes preparados: {index}')
    matched = changed = 0
    # Actualizar documentos individualmente permite reintentar en MongoDB sin replica set.
    for document in documents:
        account = str(document.get('usuario_id') or document['_id'])
        previous = document.get('password_hash')
        target = hashes[account]
        query = {'_id': document['_id'], 'password_hash': previous} if 'password_hash' in document else {'_id': document['_id'], 'password_hash': {'$exists': False}}
        result = collection.update_one(query, {'$set': {'password_hash': target}, '$unset': {'password': '', 'contrasena': '', 'clave': ''}})
        if result.matched_count != 1:
            raise CommandError(f'Cambio concurrente. Se procesaron {matched} vinculos; repite el comando para completar.')
        matched += 1
        changed += result.modified_count
        if progress and matched % 100 == 0:
            progress(f'Vinculos actualizados: {matched}')
    # Verificacion separada: no imprimir hashes ni datos personales.
    verified = 0
    for document in collection.find({}, {'usuario_id': 1, 'password_hash': 1}):
        account = str(document.get('usuario_id') or document['_id'])
        if document.get('password_hash') != hashes.get(account):
            raise CommandError('La verificacion de hashes no fue completa; repite el comando.')
        verified += 1
    if hashes and not check_password(password, next(iter(hashes.values()))):
        raise CommandError('No se pudo verificar la autenticacion con el hash generado.')
    report.update(usuarios=len(hashes), vinculos=matched, modificados=changed, verificados=verified)


def export_mongo(database, target):
    counts = Counter()
    created = False
    try:
        with target.open('x', encoding='utf-8') as output:
            created = True
            for name in sorted(database.list_collection_names()):
                if name.startswith('system.'):
                    continue
                counts[name] = 0
                for document in database[name].find({}).batch_size(500):
                    output.write(json_util.dumps({'fuente': 'mongodb', 'coleccion': name,
                        'documento': clean_document(document)}, ensure_ascii=False) + '\n')
                    counts[name] += 1
        return dict(counts)
    except Exception:
        if created:
            target.unlink(missing_ok=True)
        raise
