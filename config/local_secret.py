"""Clave JWT persistente de desarrollo; produccion puede usar DJANGO_SECRET_KEY."""
import os
import secrets


def secret_key(base_dir):
    configured=os.environ.get('DJANGO_SECRET_KEY')
    if configured: return configured
    path=base_dir / '.django-secret-key'
    try:
        with path.open('x',encoding='utf-8') as output: output.write(secrets.token_urlsafe(64))
    except FileExistsError:
        pass
    value=path.read_text(encoding='utf-8').strip()
    if len(value)<50: raise RuntimeError('La clave privada local no es valida.')
    return value
