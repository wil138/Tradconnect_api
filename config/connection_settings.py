"""Configuracion privada local; las variables de entorno tienen prioridad."""
import json
from django.core.exceptions import ImproperlyConfigured


def load_local_connections(base_dir):
    path = base_dir / 'config' / 'conexiones.local.json'
    if not path.exists():
        return {}

    try:
        with path.open('r', encoding='utf-8-sig') as fh:
            values = json.load(fh)

        if not isinstance(values, dict):
            raise ValueError()

        normalized = {}
        for key, value in values.items():
            if not isinstance(value, str):
                raise ValueError()
            normalized[key] = value.strip()

        return normalized
    except (OSError, ValueError, TypeError):
        raise ImproperlyConfigured(
            'Revisa el formato de config/conexiones.local.json; se requiere un objeto JSON con valores de texto.'
        ) from None
