"""Limpieza conservadora: conserva IDs, relaciones, importes y secretos v?lidos."""
import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal
from django.contrib.auth.hashers import identify_hasher, is_password_usable, make_password


def clean_value(value):
    if isinstance(value, str):
        # No colapsar espacios internos: pueden ser significativos.
        return unicodedata.normalize('NFC', value).replace('\x00', '').strip()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def prepare_password(value):
    """Devuelve (valor, estado). No modifica espacios ni normaliza contrase?as."""
    if value and not is_password_usable(value):
        return value, 'inutilizable'
    if value:
        try:
            hasher = identify_hasher(value)
            # identify_hasher solo detecta el prefijo; decode valida la estructura.
            hasher.decode(value)
            return value, 'conservado'
        except (ValueError, TypeError, KeyError, AssertionError):
            pass
    if not value:
        return make_password(None), 'sin_clave'
    # No convertir hashes externos/desconocidos en una contrase?a nueva.
    if '$' in value or re.fullmatch(r'[a-fA-F0-9]{32,128}', value):
        return value, 'revisar'
    return make_password(value), 'hasheado'
