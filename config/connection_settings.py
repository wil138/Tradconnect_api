"""Configuracion privada local; las variables de entorno tienen prioridad."""
import json
from django.core.exceptions import ImproperlyConfigured


def load_local_connections(base_dir):
    path=base_dir/'config'/'conexiones.local.json'
    if not path.exists(): return {}
    try:
        values=json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(values,dict) or any(not isinstance(value,str) for value in values.values()):
            raise ValueError()
        return values
    except (OSError,ValueError):
        raise ImproperlyConfigured('Revisa el formato de config/conexiones.local.json; se requiere un objeto JSON con valores de texto.') from None
