"""Selecciona conexiones locales o remotas configuradas en el entorno."""
import json
from django.core.exceptions import ImproperlyConfigured


def load_local_connections(base_dir):
    path=base_dir/'config'/'conexiones.example.json'
    if not path.exists(): return {}
    try:
        values=json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(values,dict) or any(not isinstance(value,str) for value in values.values()):
            raise ValueError()
        return values
    except (OSError,ValueError):
        raise ImproperlyConfigured('Revisa el formato de config/conexiones.example.json; se requiere un objeto JSON con valores de texto.') from None


def parse_sqlserver_connection_string(value):
    """Convierte una cadena ODBC SQL Server en los campos que usa Django."""
    aliases = {
        'server': 'HOST',
        'data source': 'HOST',
        'address': 'HOST',
        'addr': 'HOST',
        'network address': 'HOST',
        'initial catalog': 'NAME',
        'database': 'NAME',
        'user id': 'USER',
        'uid': 'USER',
        'user': 'USER',
        'password': 'PASSWORD',
        'pwd': 'PASSWORD',
    }
    parts = {}
    segments = []
    current = []
    in_braces = False
    index = 0
    while index < len(value):
        char = value[index]
        value_part = ''.join(current).rsplit('=', 1)[-1]
        if char == '{' and '=' in ''.join(current) and not value_part.strip():
            in_braces = True
            current.append(char)
        elif char == '}' and in_braces:
            if index + 1 < len(value) and value[index + 1] == '}':
                current.extend(('}', '}'))
                index += 1
            else:
                in_braces = False
                current.append(char)
        elif char == ';' and not in_braces:
            segments.append(''.join(current))
            current = []
        else:
            current.append(char)
        index += 1
    if in_braces:
        raise ImproperlyConfigured('CLOUD_SQLSERVER_CONNECTION_STRING contiene un valor entre llaves sin cerrar.')
    segments.append(''.join(current))

    for segment in segments:
        if '=' not in segment:
            continue
        key, item = segment.split('=', 1)
        field = aliases.get(key.strip().casefold())
        if field:
            item = item.strip()
            if item.startswith('{'):
                if not item.endswith('}'):
                    raise ImproperlyConfigured('CLOUD_SQLSERVER_CONNECTION_STRING contiene un valor entre llaves sin cerrar.')
                item = item[1:-1].replace('}}', '}')
            parts[field] = item

    if not parts.get('HOST') or not parts.get('NAME') or not parts.get('USER') or not parts.get('PASSWORD'):
        raise ImproperlyConfigured(
            'CLOUD_SQLSERVER_CONNECTION_STRING debe incluir Server, Initial Catalog, User ID y Password.'
        )
    return parts


def load_database_connections(environ, local_connections):
    profile = environ.get('DATABASE_PROFILE', 'local').strip().lower()
    if profile == 'local':
        return {
            'profile': profile,
            'sql': {
                'HOST': environ.get('SQLSERVER_HOST', local_connections.get('SQLSERVER_HOST', r'.\WIL')),
                'NAME': environ.get('SQLSERVER_DATABASE', local_connections.get('SQLSERVER_DATABASE', 'TradConnect')),
                'PORT': environ.get('SQLSERVER_PORT', local_connections.get('SQLSERVER_PORT', '')),
                'USER': environ.get('SQLSERVER_USER', local_connections.get('SQLSERVER_USER', '')),
                'PASSWORD': environ.get('SQLSERVER_PASSWORD', local_connections.get('SQLSERVER_PASSWORD', '')),
                'DRIVER': environ.get('SQLSERVER_DRIVER', local_connections.get('SQLSERVER_DRIVER', 'ODBC Driver 18 for SQL Server')),
                'EXTRA_PARAMS': 'TrustServerCertificate=yes',
            },
            'mongodb_uri': environ.get('MONGODB_URI', local_connections.get('MONGODB_URI')),
            'mongodb_database': environ.get('MONGODB_DATABASE', local_connections.get('MONGODB_DATABASE', 'tradconnect_db')),
        }
    if profile != 'cloud':
        raise ImproperlyConfigured('DATABASE_PROFILE debe ser "local" o "cloud".')

    connection_string = environ.get('CLOUD_SQLSERVER_CONNECTION_STRING', '')
    mongodb_uri = environ.get('CLOUD_MONGODB_URI', '')
    mongodb_database = environ.get('CLOUD_MONGODB_DATABASE', '')
    if not connection_string or not mongodb_uri or not mongodb_database:
        raise ImproperlyConfigured(
            'El perfil cloud requiere CLOUD_SQLSERVER_CONNECTION_STRING, CLOUD_MONGODB_URI y CLOUD_MONGODB_DATABASE.'
        )
    return {
        'profile': profile,
        'sql': {
            **parse_sqlserver_connection_string(connection_string),
            'PORT': '',
            'DRIVER': environ.get('CLOUD_SQLSERVER_DRIVER', 'ODBC Driver 18 for SQL Server'),
            'EXTRA_PARAMS': 'Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30',
        },
        'mongodb_uri': mongodb_uri,
        'mongodb_database': mongodb_database,
    }
